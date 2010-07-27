# xmlobject-backed django form (analogous to django db model forms)
# this code borrows heavily from django.forms.models

from collections import defaultdict
from string import capwords

from django.forms import BaseForm, CharField, IntegerField, BooleanField, \
        ChoiceField
from django.forms.forms import NON_FIELD_ERRORS
from django.forms.forms import get_declared_fields
from django.forms.models import ModelFormOptions
from django.utils.datastructures  import SortedDict
from django.utils.safestring  import mark_safe

from eulcore import xmlmap

def fieldname_to_label(name):
    """Default conversion from xmlmap Field variable name to Form field label:
    convert '_' to ' ' and capitalize words."""
    # NOTE: xmlmap fields have nothing analogous to django model fields verbose_name
    # Doing a rough-conversion from variable name to a default
    # human-readable version for formfield labels
    return capwords(name.replace('_', ' '))


def _parse_field_list(fieldnames, include_parents=False):
    field_parts = (name.split('.') for name in fieldnames)
    return _collect_fields(field_parts, include_parents)

def _collect_fields(field_parts_list, include_parents):
    fields = []
    subpart_lists = defaultdict(list)

    for parts in field_parts_list:
        field, subparts = parts[0], parts[1:]
        if subparts:
            if include_parents and field not in fields:
                fields.append(field)
            subpart_lists[field].append(subparts)
        else:
            fields.append(field)

    subfields = dict((field, _collect_fields(subparts, include_parents))
                     for field, subparts in subpart_lists.iteritems())

    return _ParsedFieldList(fields, subfields)

class _ParsedFieldList(object):
    def __init__(self, fields, subfields):
        self.fields = fields
        self.subfields = subfields
        

class SubformAwareModelFormOptions(ModelFormOptions):
    def __init__(self, options=None):
        super(SubformAwareModelFormOptions, self).__init__(options)

        self.parsed_fields = None
        if isinstance(self.fields, _ParsedFieldList):
            self.parsed_fields = self.fields
        elif self.fields is not None:
            self.parsed_fields = _parse_field_list(self.fields, include_parents=True)

        self.parsed_exclude = None
        if isinstance(self.exclude, _ParsedFieldList):
            self.parsed_exclude = self.exclude
        elif self.exclude is not None:
            self.parsed_exclude = _parse_field_list(self.exclude, include_parents=False)


def formfields_for_xmlobject(model, fields=None, exclude=None, widgets=None, options=None):
    """
    Returns two sorted dictionaries (:class:`django.utils.datastructures.SortedDict`).
     * The first is a dictionary of form fields based on the
       :class:`~eulcore.xmlmap.XmlObject` class fields and their types.
     * The second is a sorted dictionary of subform classes for any fields of type
       :class:`~eulcore.xmlmap.fields.NodeField` on the model.

    Default sorting (within each dictionary) is by XmlObject field creation order.

    Used by :class:`XmlObjectFormType` to set up a new :class:`XmlObjectForm`
    class.

    :param fields: optional list of field names; if specified, only the named fields
                will be returned, in the specified order
    :param exclude: optional list of field names that should not be included on
                the form; if a field is listed in both ``fields`` and ``exclude``,
                it will be excluded
    :param widgets: optional dictionary of widget options to be passed to form
                field constructor, keyed on field name
    """

    # first collect fields and excludes for the form and all subforms. base
    # these on the specified options object unless overridden in args.
    fieldlist = getattr(options, 'parsed_fields', None)
    if isinstance(fields, _ParsedFieldList):
        fieldlist = fields
    elif fields is not None:
        fieldlist = _parse_field_list(fields, include_parents=True)

    excludelist = getattr(options, 'parsed_exclude', None)
    if isinstance(fields, _ParsedFieldList):
        fieldlist = fields
    elif exclude is not None:
        excludelist = _parse_field_list(exclude, include_parents=False)

    if widgets is None and options is not None:
        widgets = options.widgets

    # collect the fields (unordered for now) that we're going to be returning
    formfields = {}
    subforms = {}
    field_order = {}

    for name, field in model._fields.iteritems():
        if fieldlist and not name in fieldlist.fields:
            # if specific fields have been requested and this is not one of them, skip it
            continue
        if excludelist and name in excludelist.fields:
            # if exclude has been specified and this field is listed, skip it
            continue
        if widgets and name in widgets:
            # if a widget has been specified for this field, pass as option to form field init
            kwargs = {'widget': widgets[name] }
        else:
            kwargs = {}
        # get apppropriate form widget based on xmlmap field type
        field_type = None
        if hasattr(field, 'choices') and field.choices:
            # if a field has choices defined, use a choice field (no matter what base type)
            field_type = ChoiceField
            kwargs['choices'] = [(val, val) for val in field.choices]
        elif isinstance(field, xmlmap.fields.StringField):
            field_type = CharField
        elif isinstance(field, xmlmap.fields.IntegerField):
            field_type = IntegerField
        elif isinstance(field, xmlmap.fields.SimpleBooleanField):
            # by default, fields are required - for a boolean, required means it must be checked
            # since that seems nonsensical and not useful for a boolean,
            # setting required to False to allow True or False values
            kwargs['required'] = False
            field_type = BooleanField
            
        # datefield ? - not yet well-supported; leaving out for now        
        # ... should probably distinguish between date and datetime field
        
        elif isinstance(field, xmlmap.fields.NodeField):
            # define a new xmlobject form for the nodefield class
            # grab any options passed in for fields under this one
            subform_opts = {
                'fields': fieldlist.subfields[name] if fieldlist and name in fieldlist.subfields else None,
                'exclude': excludelist.subfields[name] if excludelist and name in excludelist.subfields else None,
                'widgets': widgets[name] if widgets and name in widgets else None,
            }
            subforms[name] = xmlobjectform_factory(field.node_class, **subform_opts)
        else:
            # raise exception for unsupported fields
            # currently doesn't handle list fields
            raise Exception('XmlObjectForm does not yet support auto form field generation for %s.' \
                            % field.__class__)
           
        # TODO: list variants (currently not settable in xmlobject)... use formsets ?

        if field_type is not None:
            formfields[name] = field_type(label=fieldname_to_label(name), **kwargs)
            
        # create a dictionary indexed by field creation order, for default field ordering
        field_order[field.creation_counter] = name

    # if fields were explicitly specified, return them in that order
    if fieldlist:
        ordered_fields = SortedDict((name, formfields[name])
                                    for name in fieldlist.fields
                                    if name in formfields)
        ordered_subforms = SortedDict((name, subforms[name])
                                      for name in fieldlist.fields
                                      if name in subforms)
    else:
        # sort on field creation counter and generate a django sorted dictionary
        ordered_fields = SortedDict(
            [(field_order[key], formfields[field_order[key]]) for key in sorted(field_order.keys())
                                                if field_order[key] in formfields ]
        )
        ordered_subforms = SortedDict(
            [(field_order[key], subforms[field_order[key]]) for key in sorted(field_order.keys())
                                                if field_order[key] in subforms ]
        )
    return ordered_fields, ordered_subforms


def xmlobject_to_dict(instance, fields=None, exclude=None):
    """
    Generate a dictionary based on the data in an XmlObject instance to pass as
    a Form's ``initial`` keyword argument.

    :param instance: instance of :class:`~eulcore.xmlmap.XmlObject`
    :param fields: optional list of fields - if specified, only the named fields
            will be included in the data returned
    :param exclude: optional list of fields to exclude from the data
    """
    data = {}

    for name, field in instance._fields.iteritems():
        # not editable?
        if fields and not name in fields:
            continue
        if exclude and name in exclude:
            continue
        if isinstance(field, xmlmap.fields.NodeField):
            # XXX: importing nodefields directly: will this cause key
            # conflicts if multiple nodefields have subfields with the same
            # names?
            nodefield = getattr(instance, name)
            if nodefield is not None:
                data.update(xmlobject_to_dict(nodefield))   # fields/exclude
        else:
            data[name] = getattr(instance, name)

    return data

class XmlObjectFormType(type):
    """
    Metaclass for :class:`XmlObject`.

    Analogous to, and substantially based on, Django's ``ModelFormMetaclass``.

    Initializes the XmlObjectForm based on the :class:`~eulcore.xmlmap.XmlObject`
    instance associated as a model. Adds form fields for supported
    :class:`~eulcore.xmlmap.fields.Field`s and 'subform' XmlObjectForm classes
    for any :class:`~eulcore.xmlmap.fields.NodeField` to the Form object.
    """
    def __new__(cls, name, bases, attrs):
        # do we need to handle inheritance like django does?
        declared_fields = get_declared_fields(bases, attrs, False)
        
        new_class = super(XmlObjectFormType, cls).__new__(cls, name, bases, attrs)

        # use django's default model form options for fields, exclude, widgets, etc.
        opts = new_class._meta =  SubformAwareModelFormOptions(getattr(new_class, 'Meta',  None))
        if opts.model:
            # if a model is defined, get xml fields and any subform classes
            fields, subforms = formfields_for_xmlobject(opts.model, options=opts)

            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)

            # store all of the dynamically generated xmlobjectforms for nodefields
            new_class.subforms = subforms
        else:
            fields = declared_fields
            new_class.subforms = {}
            
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class


class XmlObjectForm(BaseForm):
    """Django Form based on an :class:`~eulcore.xmlmap.XmlObject` model,
    analogous to Django's ModelForm.

    Note that not all :mod:`eulcore.xmlmap.fields` are currently supported; all
    released field types are supported in their single-node variety, but no list
    field types are currently supported.  Attempting to define an XmlObjectForm
    without excluding unsupported fields will result in an Exception.

    Unlike Django's ModelForm, which provides a save() method, XmlObjectForm
    provides analogous functionality via :meth:`update_instance`.  Since an
    XmlObject by itself does not have a save method, and can only be saved in
    particular contexts (e.g., :mod:`eulcore.existdb` or :mod:`eulcore.fedora`),
    there is no meaningful way for an XmlObjectForm to save an associated model
    instance to the appropriate datastore.

    If you wish to customize the html display for an XmlObjectForm, rather than
    using the built-in form display functions, be aware that if your XmlObject
    has any fields of type :class:`~eulcore.xmlmap.fields.NodeField`, you should
    make sure to display the subforms for those fields.

    NOTE: If your XmlObject includes NodeField elements and you want to be able
    to dynamically add xml fields under those NodeFields, you must currently set
    instantiate_on_get to True when declaring your NodeFields.
    """

    # django has a basemodelform with all the logic
    # and then a modelform with the metaclass declaration; do we need that?
    __metaclass__ = XmlObjectFormType

    _html_section = None    # formatting for outputting object with subform

    subforms = {}
    """Sorted Dictionary of :class:`XmlObjectForm` instances for fields of type
    :class:`~eulcore.xmlmap.fields.NodeField` belonging to this Form's
    :class:`~eulcore.xmlmap.XmlObject` model, keyed on field name.  Ordered by
    field creation order or by specified fields."""

    def __init__(self, data=None, instance=None, prefix=None):
        opts = self._meta
        if instance is None:
            if opts.model is None:
                raise ValueError('XmlObjectForm has no XmlObject model class specified')
            # if we didn't get an instance, instantiate a new one
            # NOTE: if this is a subform, the data won't go anywhere useful
            # currently requires that instantiate_on_get param be set to True for NodeFields
            self.instance = opts.model()
            # track adding new instance instead of updating existing?

            object_data = {}    # no initial data
        else:
            self.instance = instance
            # generate dictionary of initial data based on current instance
            object_data = xmlobject_to_dict(self.instance)  # fields, exclude?

        # initialize subforms for all nodefields that belong to the xmlobject model
        self._init_subforms(data)
            
        super(XmlObjectForm, self).__init__(data=data, initial=object_data, prefix=prefix)
        # possible additional params :
        #    files, auto_id, object_data,
        #    error_class, label_suffix, empty_permitted

    def _init_subforms(self, data=None):
        # initialize each subform class with the appropriate model instance and data
        self.subforms = {}
        for name, subform in self.__class__.subforms.iteritems():
            # instantiate the new form with the current field as instance, if available
            if self.instance is not None:
                # get the relevant instance for the current NodeField variable
                subinstance = getattr(self.instance, name, None)
            else:
                subinstance = None
    
            # FIXME: do prefixes need to be nested?
            # e.g., subform prefix = my prefix + name

            # instantiate the subform class with field data and model instance
            # - setting prefix based on field name, to distinguish similarly named fields
            self.subforms[name] = subform(data=data, instance=subinstance, prefix=name)

    def update_instance(self):
        """Save bound form data into the XmlObject model instance and return the
        updated instance."""
        opts = self._meta
        for name in self.instance._fields.iterkeys():
            if opts.fields and name not in opts.parsed_fields.fields:
                continue
            if opts.exclude and name in opts.parsed_exclude.fields:
                continue
            if name in self.cleaned_data:
                setattr(self.instance, name, self.cleaned_data[name])

        # update sub-model portions via any subforms
        for subform in self.subforms.itervalues():
            subform.update_instance()

        return self.instance
    
    # NOTE: django model form has a save method - not applicable here,
    # since an XmlObject by itself is not expected to have a save method
    # (only likely to be saved in context of a fedora or exist object)

    def is_valid(self):
        """Returns True if this form and all subforms (if any) are valid.
        
        If all standard form-validation tests pass, uses :class:`~eulcore.xmlmap.XmlObject`
        validation methods to check for schema-validity (if a schema is associated)
        and reporting errors.  Additonal notes:
        
         * schema validation requires that the :class:`~eulcore.xmlmap.XmlObject`
           be initialized with the cleaned form data, so if normal validation
           checks pass, the associated :class:`~eulcore.xmlmap.XmlObject` instance
           will be updated with data via :meth:`update_instance`
         * schema validation errors SHOULD NOT happen in a production system

        :rtype: boolean
        """
        valid = super(XmlObjectForm, self).is_valid() and \
                all([s.is_valid() for s in self.subforms.itervalues()])
        # schema validation can only be done after regular validation passes,
        # because xmlobject must be updated with cleaned_data
        if valid and self.instance is not None:
            # update instance required to check schema-validity
            instance = self.update_instance()     
            if instance.is_valid():
                return True
            else:
                # if not schema-valid, add validation errors to error dictionary
                # NOTE: not overriding _get_errors because that is used by the built-in validation
                # append to any existing non-field errors
                if NON_FIELD_ERRORS not in self._errors:
                    self._errors[NON_FIELD_ERRORS] = self.error_class()
                self._errors[NON_FIELD_ERRORS].append("There was an unexpected schema validation error.  " +
                    "This should not happen!  Please report the following errors:")
                for err in instance.validation_errors():
                    self._errors[NON_FIELD_ERRORS].append('VALIDATION ERROR: %s' % err.message)               
                return False
        return valid

    # NOTE: errors only returned for the *current* form, not for all subforms
    # - appears to be used only for form output, so this should be sensible

    def _html_output(self, normal_row, error_row, row_ender,  help_text_html, errors_on_separate_row):
        """Extend BaseForm's helper function for outputting HTML. Used by as_table(), as_ul(), as_p().
        
        Combines the HTML version of the main form's fields with the HTML content
        for any subforms.
        """
        parts = []
        parts.append(super(XmlObjectForm, self)._html_output(normal_row, error_row, row_ender,
                help_text_html, errors_on_separate_row))
        for name, subform in self.subforms.iteritems():
            # pass the configured html section to subform in case of any sub-subforms
            subform._html_section = self._html_section
            subform_html = subform._html_output(normal_row, error_row, row_ender,
                    help_text_html, errors_on_separate_row)
            # if html section is configured, add section label and wrapper for
            if self._html_section is not None:
                parts.append(self._html_section %
                    {'label': fieldname_to_label(name), 'content': subform_html} )
            else:
                parts.append(subform_html)

        return mark_safe(u'\n'.join(parts))

    # intercept the three standard html output formats to set an appropriate section format
    def as_table(self):
        """Behaves exactly the same as Django Form's as_table() method,
        except that it also includes the fields for any associated subforms
        in table format.

        Subforms, if any, will be grouped in a <tbody> labeled with a heading
        based on the label of the field.
        """
        self._html_section = u'<tbody><tr><th colspan="2" class="section">%(label)s</th></tr><tr><td colspan="2"><table class="subform">\n%(content)s</table></td></tr></tbody>'
        #self._html_section = u'<tbody><tr><th class="section" colspan="2">%(label)s</th></tr>\n%(content)s</tbody>'
        return super(XmlObjectForm, self).as_table()

    def as_p(self):
        """Behaves exactly the same as Django Form's as_p() method,
        except that it also includes the fields for any associated subforms
        in paragraph format.

        Subforms, if any, will be grouped in a <div> of class 'subform',
        with a heading based on the label of the field.
        """
        self._html_section = u'<div class="subform"><p class="label">%(label)s</p>%(content)s</div>'
        return super(XmlObjectForm, self).as_p()

    def as_ul(self):
        """Behaves exactly the same as Django Form's as_ul() method,
        except that it also includes the fields for any associated subforms
        in list format.

        Subforms, if any, will be grouped in a <ul> of class 'subform',
        with a heading based on the label of the field.
        """
        self._html_section = u'<li class="subform"><p class="label">%(label)s</p><ul>%(content)s</ul></li>'
        return super(XmlObjectForm, self).as_ul()


def xmlobjectform_factory(model, form=XmlObjectForm, fields=None, exclude=None,
                            widgets=None):
    """Dynamically generate a new :class:`XmlObjectForm` class using the
    specified :class:`eulcore.xmlmap.XmlObject` class.
    
    Based on django's modelform_factory.
    """

    attrs = {'model': model}
    if fields is not None:
        attrs['fields'] = fields
    if exclude is not None:
        attrs['exclude'] = exclude
    if widgets is not None:
        attrs['widgets'] = widgets
    
    # If parent form class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type('Meta', parent, attrs)

    # Give this new form class a reasonable name.
    class_name = model.__name__ + 'XmlObjectForm'

    # Class attributes for the new form class.
    form_class_attrs = {
        'Meta': Meta
        # django has a callback formfield here; do we need that?
    }

    return XmlObjectFormType(class_name, (form,), form_class_attrs)
