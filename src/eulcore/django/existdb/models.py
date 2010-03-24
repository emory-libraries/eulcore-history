from eulcore.django.existdb.manager import Manager
from eulcore.xmlmap.core import XmlObject, XmlObjectType

class _ManagerDescriptor(object):
    def __init__(self, manager):
       self.manager = manager

    def __get__(self, instance, type=None):
        if instance is not None:
            raise AttributeError, "Manager isn't accessible via %s instances" % (type.__name__,)
        return self.manager

class XmlModelType(XmlObjectType):
    def __new__(cls, name, bases, defined_attrs):
        use_attrs = {}
        managers = {}

        for attr_name, attr_val in defined_attrs.items():
            # XXX: like in XmlObjectType, not a fan of isinstance here.
            # consider using something like django's contribute_to_class.

            # in any case, we handle managers and then pass everything else
            # up to the metaclass parent (XmlObjectType) to handle other
            # things like fields.
            if isinstance(attr_val, Manager):
                manager = attr_val
                managers[attr_name] = manager
                use_attrs[attr_name] = _ManagerDescriptor(manager)

            else:
                use_attrs[attr_name] = attr_val
        use_attrs['_managers'] = managers

        # XXX: do we need to ensure a default model like django relational
        # Models do? i don't think we need it right now, but we might in the
        # future.

        super_new = super(XmlModelType, cls).__new__
        new_class = super_new(cls, name, bases, use_attrs)

        # and then patch that new class into the managers:
        for manager in managers.values():
            manager.model = new_class

        return new_class


class XmlModel(XmlObject):
    __metaclass__ = XmlModelType
