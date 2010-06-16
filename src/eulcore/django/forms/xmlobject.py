# xmlobject-backed django form (analogous to django db model forms)
# this code borrows heavily from django.forms.models

#from string import capwords    # unused - may want to use for variable name to field label conversion

from django.forms import BaseForm, CharField, IntegerField, BooleanField
from django.forms.forms import get_declared_fields
from django.forms.models import ModelFormOptions
from django.utils.datastructures  import SortedDict
from django.utils.safestring  import mark_safe

from eulcore import xmlmap

def fields_for_xmlobject(model, fields=None, exclude=None, widgets=None):
    """
    Returns a sorted dictionary (:class:`django.utils.datastructures.SortedDict`
    of form fields based on the :class:`~eulcore.xmlmap.XmlObject` instance
    fields and their types.  Default sorting is by xmlobject field creation order.

    :param fields: optional list of field names; if specified, only the named fields
    will be returned
    :param exclude: optional list of field names that should not be included on
    the form; if a field is listed in fields and exclude, exclude overrides
    :param widgets: optional dictionary of widget options to be passed to form
    field constructor, keyed on field name
    """
    formfields = {}
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
        if isinstance(field, xmlmap.fields.StringField):
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
        # should probably distinguish between date and datetime field
        
        elif isinstance(field, xmlmap.fields.NodeField):
            # not handled here, but not an error
            pass
        else:
            # raise exception for unsupported fields
            # currently doesn't handle list fields
            raise Exception('XmlObjectForm does not yet support auto form field generation for %s.' \
                            % field.__class__)
           
        # TODO: list variants (currently not settable in xmlobject)... use formsets ?

        if field_type is not None:
            # FIXME: django fields have verbose_name;
            # should we use capwords, do some other default human-readable conversion for labels?
            # using variable name as label for now
            formfields[name] = field_type(label=name, **kwargs)
            # create a dictionary indexed by field creation order, for default field ordering
            field_order[field.creation_counter] = name

    # if fields were explicitly specified, return them in that order
    if fields:
        ordered_fields = SortedDict([(name, formfields[name]) for name in fields])
    else:
        # sort on field creation counter and generate a django sorted dictionary
        ordered_fields = SortedDict(
            [(field_order[key], formfields[field_order[key]]) for key in sorted(field_order.keys())]
        )    
    return ordered_fields


def subforms_for_xmlobject(model, data=None, instance=None, fields=None, exclude=None):
    # generate a form for each nodefield in the model
    subforms = []
    for name, field in model._fields.iteritems():
        if fields and not name in fields:
            # if specific fields have been requested and this is not one of them, skip it
            continue
        if exclude and name in exclude:
            # if exclude has been specified and this field is listed, skip it
            continue
        if isinstance(field, xmlmap.fields.NodeField):
            # define a new xmlobject form for the nodefield class
            newform = xmlobjectform_factory(field.node_class)
            # instantiate the new form with the current field as instance, if available
            if instance is not None:
                # get the relevant instance for the current NodeField variable
                subinstance = getattr(instance, name) or None
            else:
                subinstance = None

            if data is not None:
                # pull out any relevant initial data by name prefix
                # (could hand off all the data, but it seems cleaner to pass on the appropriate subset)
                id_prefix = '%s-' % name
                field_data = dict([(k, v) for k, v in data.items()
                                            if k.startswith(id_prefix) ])
            else:
                field_data = None
            

            # initialize with a prefix based on field name,
            # so similarly named fields can be distinguished
            subforms.append(newform(data=field_data, instance=subinstance, prefix=name))
            
    return subforms    

def xmlobject_to_dict(instance, fields=None, exclude=None):
    # generate a dict with data in xmlobject instance to pass as form's initial value
    data = {}

    for name, field in instance._fields.iteritems():
        # not editable?
        # TODO: handle fields/exclude
        if isinstance(field, xmlmap.fields.NodeField):
            nodefield = getattr(instance, name)
            if nodefield is not None:
                data.update(xmlobject_to_dict(nodefield))   # fields/exclude
        else:
            data[name] = getattr(instance, name)

    return data

class XmlObjectFormType(type):
    # metaclass for xmlobjectform
    # adds appropriate form fields to the Form object based on the XmlObject fields

    def __new__(cls, name, bases, attrs):
        # do we need to handle inheritance like django does?
        declared_fields = get_declared_fields(bases, attrs, False)
        
        new_class = super(XmlObjectFormType, cls).__new__(cls, name, bases, attrs)

        # use django's default model form options for fields, exclude, widgets, etc.
        opts = new_class._meta =  ModelFormOptions(getattr(new_class, 'Meta',  None))
        if opts.model:
            # if a model is defined, get xml fields
            fields = fields_for_xmlobject(opts.model, opts.fields,
                                      opts.exclude, opts.widgets)

            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
            
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class


class XmlObjectForm(BaseForm):
    """Django Form object based on an XmlObject, analogous to Django's ModelForm."""

    # django has a basemodelform with all the logic
    # and then a modelform with the metaclass declaration; do we need that?
    __metaclass__ = XmlObjectFormType

    _html_section = None    # formatting for outputting object with subform

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

        # generate subforms for all nodefields that belong to our xmlobject model
        # - processing here instead of in metaclass new because subforms need
        #   access to the model instance to set initial data properly
        # FIXME: define subform classes in metaclass new,
        # then initialize the subform class instances here with data & instance
        # TODO: store name of nodefield to associate with subform? (and order like fields?)
        self.subforms = subforms_for_xmlobject(opts.model, data, self.instance,
            fields=self._meta.fields, exclude=self._meta.exclude)
        # TODO:
        # - document so custom form output can be done reasonably with subforms
            
        super(XmlObjectForm, self).__init__(data=data, initial=object_data, prefix=prefix)
        # possible params to pass:
        #    data, files, auto_id, object_data,
        #    error_class, label_suffix, empty_permitted

    def update_instance(self):
        "Save bound form data into the model instance and return the instance."
        for name, field in self.instance._fields.iteritems():
            if self._meta.fields and name not in self._meta.fields:
                continue
            if name in self.cleaned_data:
                setattr(self.instance, name, self.cleaned_data[name])

        # update sub-model portions via any subforms
        for subform in self.subforms:
            subform.update_instance()

        return self.instance
    
    # NOTE: django model form has a save method - not applicable here,
    # since an XmlObject by itself is not expected to have a save method
    # (only likely to be saved in context of a fedora or exist object)

    def is_valid(self):
        # check if this form AND all of its subforms are valid
        # FIXME: test!
        return super(XmlObjectForm, self).is_valid() and all([s.is_valid() for s in self.subforms])

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
        for subform in self.subforms:           
            subform_html = subform._html_output(normal_row, error_row, row_ender,
                    help_text_html, errors_on_separate_row)
            # if html section is configured, add section label and wrapper for
            # FIXME: subform name/label ?
            if self._html_section is not None:
                parts.append(self._html_section %
                    {'label': 'subform section', 'content': subform_html} )
            else:
                parts.append(subform_html)

        return mark_safe(u'\n'.join(parts))

    # intercept the three standard html output formats to set an appropriate section format
    def as_table(self):
        self._html_section = u'<tbody><tr><th colspan="2">%(label)s</th></tr>\n%(content)s</tbody>'
        return super(XmlObjectForm, self).as_table()

    def as_p(self):
        self._html_section = u'<div class="subform"><p class="label">%(label)s</p>%(content)s</div>'
        return super(XmlObjectForm, self).as_p()

    def as_ul(self):
        self._html_section = u'<li class="subform"><p class="label">%(label)s</p><ul>%(content)s</ul></li>'
        return super(XmlObjectForm, self).as_ul()


def xmlobjectform_factory(model, form=XmlObjectForm, fields=None, exclude=None):
    """Dynamically generate a new XmlObjectForm class from a specified xmlobject class.
    
    Based on django's modelform_factory.
    """

    attrs = {'model': model}
    if fields is not None:
        attrs['fields'] = fields
    if exclude is not None:
        attrs['exclude'] = exclude

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
