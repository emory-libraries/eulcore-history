# xmlobject-backed django form (analogous to django db model forms)
# this code borrows heavily from django.forms.models

from string import capwords

from django.forms import BaseForm, CharField, IntegerField, BooleanField
from django.forms.forms import get_declared_fields
from django.forms.models import ModelFormOptions

from eulcore import xmlmap

def fields_for_xmlobject(model, fields=None, exclude=None, widgets=None):
    """
    Returns a dictionary of form fields based on the :class:`~eulcore.xmlmap.XmlObject`
    instance fields and their types.

    :param fields: optional list of field names; if specified, only the named fields
    will be returned 
    """
    formfields = {}
    
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
            field_type = BooleanField
        # datefield?
        else:
            pass
            # is there any possible sane fall back ? error or warn here?
            # currently can't handle list fields...
            # nodefields handled via subforms 

        # TODO: list variants (currently not settable in xmlobject)... use formsets ?

        if field_type is not None:
            # FIXME: django fields have verbose_name; use capwords, do other default conversion for label?
            formfields[name] = field_type(label=name, **kwargs)   # use name as label for now

    # TODO: handle fields, exclude, widgets, sorting
    return formfields

def subforms_for_xmlobject(model, instance=None):
    # generate a sub-form for each nodefield in the model
    # NOTE: untested, not sure how we want to handle this
    subforms = []
    for name, field in model._fields.iteritems():
        if isinstance(field, xmlmap.fields.NodeField):
            # define a new xmlobject form for the nodefield class
            newform = xmlobjectform_factory(field.node_class)
            # instantiate the new form with the current field as instance, if available
            if instance is not None:
                subinstance = getattr(instance, name) or None
            else:
                subinstance = None

            subforms.append(newform(instance=subinstance, prefix=name))
    return subforms    

def xmlobject_to_dict(instance, fields=None, exclude=None):
    # generate a dict with data in xmlobject instance to pass as form's initial value
    data = {}

    for name, field in instance._fields.iteritems():
        # not editable?
        # handle fields/exclude
        if isinstance(field, xmlmap.fields.NodeField):
            nodefield = getattr(instance, name)
            if nodefield is not None:
                data.update(xmlobject_to_dict(nodefield))   # fields/exclude
        else:
            data[name] = getattr(instance, name)

    return data


def save_instance(form, instance, fields=None):
    # save bound form data into a model instance
    for name, field in instance._fields.iteritems():
        if fields and name not in fields:
            continue
        if name in form.cleaned_data:
            setattr(instance, name, form.cleaned_data[name])

    return instance


class XmlObjectFormType(type):
    # metaclass for xmlobjectform

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
    # django has a basemodelform with all the logic
    # and then a modelform with the metaclass declaration; do we need that?
    __metaclass__ = XmlObjectFormType
     
    def __init__(self, instance=None, prefix=None):
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

        # TODO: figure out how to handle nodefields properly
        self.subforms = subforms_for_xmlobject(opts.model, self.instance)
            
        super(XmlObjectForm, self).__init__(initial=object_data, prefix=prefix)
        # possible params to pass:
        #    data, files, auto_id, prefix,  object_data,
        #    error_class, label_suffix, empty_permitted

    def save(self):
        return save_instance(self, self.instance, self._meta.fields)

def xmlobjectform_factory(model, form=XmlObjectForm, fields=None, exclude=None):
    # dynamically generate an xmlobjectform from a specified xmlobject class
    # - based on django's modelform_factory

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
