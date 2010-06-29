# xmlobject-backed django form (analogous to django db model forms)
# this code borrows heavily from django.forms.models

from string import capwords

from django.forms import BaseForm, CharField, IntegerField, BooleanField, \
        DateField, ChoiceField
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


def formfields_for_xmlobject(model, fields=None, exclude=None, widgets=None):
    """
    Returns two sorted dictionaries (:class:`django.utils.datastructures.SortedDict`).
     * The first is a dictionary of form fields based on the
       :class:`~eulcore.xmlmap.XmlObject` class fields and their types.
     * The second is a sorted dictionary of subform classes for any  fields of type
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
    formfields = {}
    subforms = {}
    field_order = {}
    
    for name, field in model._fields.iteritems():
        if fields and not name in fields:
            # if specific fields have been requested and this is not one of them, skip it
            continue
        if exclude and name in exclude:
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
        #elif isinstance(field, xmlmap.fields.DateField):
        #    field_type = DateField
        
        # should probably distinguish between date and datetime field
        
        elif isinstance(field, xmlmap.fields.NodeField):
            # define a new xmlobject form for the nodefield class
            # grab any options passed in for fields under this one
            subform_opts = {
                'fields': fields[name] if fields and name in fields else None,
                'exclude': exclude[name] if exclude and name in exclude else None,
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
    if fields:
        ordered_fields = SortedDict([(name, formfields[name]) for name in fields
                                                if name in formfields ])
        ordered_subforms = SortedDict([(name, subforms[name]) for name in fields
                                                if name in subforms ])
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
        opts = new_class._meta =  ModelFormOptions(getattr(new_class, 'Meta',  None))
        if opts.model:
            # if a model is defined, get xml fields and any subform classes
            fields, subforms = formfields_for_xmlobject(opts.model, opts.fields,
                                      opts.exclude, opts.widgets)

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
            self.instance = opts.model()            
            # track adding new instance instead of updating existing?

            object_data = {}    # no initial data
        else:
            self.instance = instance
            # generate dictionary of initial data based on current instance
            object_data = xmlobject_to_dict(self.instance)  # fields, exclude?

        # initialize subforms for all nodefields that belong to the xmlobject model
        self._init_subforms(data)
        # TODO:
        # - document so custom form output can be done reasonably with subforms
            
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
                subinstance = getattr(self.instance, name) or None
            else:
                subinstance = None

            if data is not None:
                # field name will be used as form prefix
                # pull out any relevant initial data by name prefix
                # (could hand off all the data, but it seems cleaner to pass on the appropriate subset)
                id_prefix = '%s-' % name
                field_data = dict([(k, v) for k, v in data.items()
                                            if k.startswith(id_prefix) ])
            else:
                field_data = None
    
            # FIXME: do prefixes need to be nested?
            # e.g., subform prefix = my prefix + name

            # instantiate the subform class with field data and model instance
            # - setting prefix based on field name, to distinguish similarly named fields
            self.subforms[name] = subform(data=data, instance=subinstance, prefix=name)

    def update_instance(self):
        """Save bound form data into the XmlObject model instance and return the
        updated instance."""
        for name in self.instance._fields.iterkeys():
            if self._meta.fields and name not in self._meta.fields:
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
        "Returns True if this form and all subforms (if any) are valid."
        return super(XmlObjectForm, self).is_valid() and \
                    all([s.is_valid() for s in self.subforms.itervalues()])

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
