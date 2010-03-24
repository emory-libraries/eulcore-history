from datetime import datetime

from Ft.Lib import Uri
from Ft.Xml.Domlette import NonvalidatingReader
from Ft.Xml.XPath import Compile, Evaluate
from Ft.Xml.XPath.Context import Context
from Ft.Xml.Xslt import Processor

from eulcore.xmlmap.fields import Field

__all__ = [ 'XmlObject', 'parseUri', 'parseString',
    'load_xmlobject_from_string', 'load_xmlobject_from_file' ]

parseUri = NonvalidatingReader.parseUri
parseString = NonvalidatingReader.parseString

class _FieldDescriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, objtype):
        if obj is None:
            return self
        return self.field.get_for_node(obj.dom_node, obj.context)


class XmlObjectType(type):
    def __new__(cls, name, bases, defined_attrs):
        use_attrs = {}
        fields = {}
        recursive_fields = []

        # inherit base fields first; that way current class field defs will
        # override parents. note that since the parents already added fields
        # from *their* parents (because they were built from XmlObjectType),
        # we don't have to recurse.
        for base in bases:
            base_fields = getattr(base, '_fields', None)
            if base_fields:
                fields.update(base_fields)

        for attr_name, attr_val in defined_attrs.items():
            # XXX: not a fan of isintance here. maybe use something like
            # django's contribute_to_class?
            if isinstance(attr_val, Field):
                field = attr_val
                fields[attr_name] = field
                use_attrs[attr_name] = _FieldDescriptor(field)

                # collect self-referential NodeFields so that we can resolve
                # them once we've created the new class
                node_class = getattr(field, 'node_class', None)
                if isinstance(node_class, basestring):
                    if node_class in ('self', name):
                        recursive_fields.append(field)
                    else:
                        msg = ('Class %s has field %s with node_class %s, ' +
                               'but the only supported class names are ' +
                               '"self" and %s.') % (name, attr_val,
                                                    repr(node_class),
                                                    repr(name))
                        raise ValueError(msg)

            else:
                use_attrs[attr_name] = attr_val
        use_attrs['_fields'] = fields

        super_new = super(XmlObjectType, cls).__new__
        new_class = super_new(cls, name, bases, use_attrs)

        # patch self-referential NodeFields (collected above) with the
        # newly-created class
        for field in recursive_fields:
            assert field.node_class in ('self', name)
            field.node_class = new_class

        return new_class


class XmlObject(object):

    """A Python object wrapped around an XML DOM node.

    Typical programs will define subclasses of :class:`XmlObject` with
    various field members. Generally they will use
    :func:`load_xmlobject_from_string` and :func:`load_xmlobject_from_file`
    to create instances of these subclasses, though they can be constructed
    directly if more control is necessary.

    In particular, programs can pass an optional
    :class:`Ft.Xml.XPath.Context` argument to the constructor to specify an
    XPath evaluation context with alternate namespace or variable
    definitions. By default, fields are evaluated in an XPath context
    containing the namespaces of the wrapped DOM node and no variables.

    """

    __metaclass__ = XmlObjectType

    def __init__(self, dom_node, context=None):
        self.dom_node = dom_node
        self.context = context or Context(dom_node, 
            processorNss=dict([(n.localName, n.value) for n in dom_node.xpathNamespaces]))

    def xslTransform(self, filename=None, xsl=None, params={}):
        """Run an xslt transform on the contents of the XmlObject.

        XSLT can be passed as filename or string. If a params dictionary is
        specified, its items will be passed as parameters to the XSL
        transformation.

        """
        xslproc = Processor.Processor()
        if filename is not None:
            xslt = parseUri(Uri.OsPathToUri(filename))
        if xsl is not None:
            xslt = parseString(xsl, "urn:bogus")
        xslproc.appendStylesheetNode(xslt)
        return xslproc.runNode(self.dom_node.ownerDocument, topLevelParams=params)

def getXmlObjectXPath(cls, var):
    """Return the xpath string for an xmlmap field that belongs to the specified XmlObject.

       If var contains '__', will generate the full xpath to a field mapped on a subobject
       (sub-object must be mapped with NodeField or NodeListField)
    """
    # FIXME: type-checking, exceptions?

    xpath_parts = []
    var_parts = var.split('__')
    var_parts.reverse() # so we can pop() them off

    while var_parts:
        var_part = var_parts.pop()
        field = cls._fields.get(var_part, None)
        if field is None: # old descriptor backward compat
            field = getattr(cls, var_part, None)
        if field is None:
            # fall back on raw xpath
            # XXX is this right? we at least need it for backward compat
            xpath_parts.append(var_part)
            xpath_parts += var_parts
            break
        xpath_parts.append(field.xpath)
        cls = getattr(field, 'node_class', None)

    return '/'.join(xpath_parts)

def load_xmlobject_from_string(string, xmlclass=XmlObject):
    """Initialize an XmlObject from a string.

    If an xmlclass is specified, construct an instance of that class instead
    of XmlObject. It should be a subclass of XmlObject. The constructor will
    be passed a single DOM node.
    
    """
    # parseString wants a uri, but context doesn't really matter for a string...
    parsed_str= parseString(string, "urn:bogus")
    return xmlclass(parsed_str.documentElement)

def load_xmlobject_from_file(filename, xmlclass=XmlObject):
    """Initialize an XmlObject from a file.

    If an xmlclass is specified, construct an instance of that class instead
    of XmlObject. It should be a subclass of XmlObject. The constructor will
    be passed a single DOM node.
    
    """
    file_uri = Uri.OsPathToUri(filename)
    parsed_file = parseUri(file_uri)
    return xmlclass(parsed_file.documentElement)

# Import these for backward compatibility. Should consider deprecating these
# and asking new code to pull them from descriptor
from eulcore.xmlmap.fields import *
