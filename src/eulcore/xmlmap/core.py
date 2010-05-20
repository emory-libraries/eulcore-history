from Ft.Lib import Uri
from Ft.Xml.Domlette import NonvalidatingReader, CanonicalPrint, \
                            ValidatingReader, \
                            implementation as DomImplementation
from Ft.Xml.XPath.Context import Context
from Ft.Xml.Xslt import Processor
import cStringIO

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

    def __set__(self, obj, value):        
        return self.field.set_for_node(obj.dom_node, obj.context, value)


class XmlObjectType(type):

    """
    A metaclass for :class:`XmlObject`.

    Analogous in principle to Django's ``ModelBase``, this metaclass
    functions rather differently. While it'll likely get a lot closer over
    time, we just haven't been growing ours long enough to demand all of the
    abstractions built into Django's models. For now, we do three things:

      1. take any :class:`~eulcore.xmlmap.fields.Field` members and convert
         them to descriptors,
      2. store all of these fields and all of the base classes' fields in a
         ``_fields`` dictionary on the class, and
      3. if any local (non-parent) fields look like self-referential
         :class:`eulcore.xmlmap.NodeField` objects then patch them up
         to refer to the newly-created :class:`XmlObject`.

    """

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

    """
    A Python object wrapped around an XML DOM node.

    Typical programs will define subclasses of :class:`XmlObject` with
    various field members. Some programs will use
    :func:`load_xmlobject_from_string` and :func:`load_xmlobject_from_file`
    to create instances of these subclasses. Other programs will create them
    directly, passing a dom_node argument to the constructor. If the
    subclass defines a :attr:`ROOT_NAME` then this dom_node argument is
    optional: Programs may then create instances directly with no
    constructor arguments.

    Programs can also pass an optional :class:`Ft.Xml.XPath.Context`
    argument to the constructor to specify an XPath evaluation context with
    alternate namespace or variable definitions. By default, fields are
    evaluated in an XPath context containing the namespaces of the wrapped
    DOM node and no variables.
    """

    __metaclass__ = XmlObjectType

    ROOT_NAME = None
    """A default root element name (with namespace prefix) used when an object
    of this type is created from scratch."""
    ROOT_NS = None
    """The default namespace used when an object of this type is created from
    scratch."""
    EXTRA_ROOT_NAMESPACES = {}
    """A dictionary whose keys are namespace prefixes and whose values are
    namespace URIs. These namespaces are added to the root element when an
    object of this type is created from scratch."""

    def __init__(self, dom_node=None, context=None):
        if dom_node is None:
            dom_node = self._build_root_element()

        self.dom_node = dom_node
        self.context = context or Context(dom_node, 
            processorNss=dict([(n.localName, n.value) for n in dom_node.xpathNamespaces]))

    def _build_root_element(self):
        doc = DomImplementation.createDocument(self.ROOT_NS, self.ROOT_NAME, None)
        for prefix, ns in self.EXTRA_ROOT_NAMESPACES.items():
            doc.documentElement.setAttributeNS('http://www.w3.org/2000/xmlns/',
                'xmlns:' + prefix, ns)
        return doc.documentElement

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

    def __unicode__(self):
        return self.dom_node.xpath("normalize-space(.)")

    def serialize(self, stream=None):
        """Serialize the contents of the XmlObject to a stream.

        If no stream is specified, returns a string.
        """
        if stream is None:
            string_mode = True
            stream = cStringIO.StringIO()
        else:
            string_mode = False

        # NOTE: using CanonicalPrint to keep namespace declarations, etc. where they are in the original xml
        CanonicalPrint(self.dom_node, stream=stream)
        
        if string_mode:
            data = stream.getvalue()
            stream.close()
            return data
        
        return stream


def load_xmlobject_from_string(string, xmlclass=XmlObject, validate=False):
    """Initialize an XmlObject from a string.

    If an xmlclass is specified, construct an instance of that class instead
    of XmlObject. It should be a subclass of XmlObject. The constructor will
    be passed a single DOM node.
    
    """
    if validate:
        parser = ValidatingReader.parseString
    else:
        parser = NonvalidatingReader.parseString
    # parseString wants a uri, but context doesn't really matter for a string...
    parsed_str= parser(string, "urn:bogus")
    return xmlclass(parsed_str.documentElement)

def load_xmlobject_from_file(filename, xmlclass=XmlObject, validate=False):
    """Initialize an XmlObject from a file.

    If an xmlclass is specified, construct an instance of that class instead
    of XmlObject. It should be a subclass of XmlObject. The constructor will
    be passed a single DOM node.
    
    """
    if validate:
        parser = ValidatingReader.parseUri
    else:
        parser = NonvalidatingReader.parseUri

    file_uri = Uri.OsPathToUri(filename)
    parsed_file = parser(file_uri)
    return xmlclass(parsed_file.documentElement)

# Import these for backward compatibility. Should consider deprecating these
# and asking new code to pull them from descriptor
from eulcore.xmlmap.fields import *
