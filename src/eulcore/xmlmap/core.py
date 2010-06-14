import cStringIO
from lxml import etree
from lxml.builder import ElementMaker

from eulcore.xmlmap.fields import Field

__all__ = [ 'XmlObject', 'parseUri', 'parseString', 'loadSchema',
    'load_xmlobject_from_string', 'load_xmlobject_from_file' ]

def parseUri(stream, uri=None):
    """Read an XML document from a URI, and return a :mod:`lxml.etree`
    document."""
    return etree.parse(stream, base_url=uri)
def parseString(string, uri=None):
    """Read an XML document provided as a byte string, and return a
    :mod:`lxml.etree` document. String cannot be a Unicode string.
    Base_uri should be provided for the calculation of relative URIs."""
    return etree.fromstring(string, base_url=uri)
def loadSchema(uri, base_uri=None):
    """Load an XSD XML document (specified by filename or URL), and return a
    :class:`lxml.etree.XMLSchema`."""
    return etree.XMLSchema(etree.parse(uri, base_url=base_uri))

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
    # FIXME: context paragraph no longer accurate...

    __metaclass__ = XmlObjectType

    dom_node = None
    """The top-level xml node wrapped by the object"""
    
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

    XSD_SCHEMA = None
    """URI or file path to the XSD schema associated with this :class:`XmlObject`,
    if any.  If configured, will be used for optional validation when calling
    :meth:`load_xmlobject_from_string` and :meth:`load_xmlobject_from_file`,
    and with :meth:`is_valid`.
    """
    xmlschema = None 
    """A parsed XSD schema instance of :class:`lxml.etree.XMLSchema`; will be
    loaded at class initialization time if XSD_SCHEMA is set and xmlchema is None.
    If you wish to load and parse the schema at class definition time, instead
    of at class instance initialization time, you may want to define your schema
    in your subclass like this::

        XSD_SCHEMA = "http://www.openarchives.org/OAI/2.0/oai_dc.xsd"
        xmlschema = xmlmap.loadSchema(XSD_SCHEMA)     
    """    
    # NOTE: DTD and RNG validation could be handled similarly to XSD validation logic

    def __init__(self, dom_node=None, context=None):
        if dom_node is None:
            dom_node = self._build_root_element()

        self.dom_node = dom_node
        # FIXME: context probably needs work
        self.context = {'namespaces' : dom_node.nsmap}
        if context is not None:
            self.context.update(context)

        if self.XSD_SCHEMA is not None and self.xmlschema is None:
            # load xml schema if one is defined and has not already been loaded
            self.xmlschema = loadSchema(self.XSD_SCHEMA)

    def _build_root_element(self):
        opts = {}
        if hasattr(self, 'ROOT_NS'):
            opts['namespace'] = self.ROOT_NS
        if hasattr(self, 'ROOT_NAMESPACES'):
            opts['nsmap'] = self.ROOT_NAMESPACES

        E = ElementMaker(**opts)
        root = E(self.ROOT_NAME)
        return root
        

    def xslTransform(self, filename=None, xsl=None, params={}):
        """Run an xslt transform on the contents of the XmlObject.

        XSLT can be passed as filename or string. If a params dictionary is
        specified, its items will be passed as parameters to the XSL
        transformation.

        """
        if filename is not None:
            xslt_doc = etree.parse(filename)
        if xsl is not None:
            xslt_doc = etree.fromstring(xsl)
        transform = etree.XSLT(xslt_doc)
        # FIXME: this returns an etree; should it convert to string first?
        return transform(self.dom_node)

    def __unicode__(self):
        return self.dom_node.xpath("normalize-space(.)")

    def serialize(self, stream=None, pretty=False):
        """Serialize the contents of the XmlObject to a stream.

        If no stream is specified, returns a string.
        :param stream: stream or other file-like object to write content to (optional)
        :param pretty: pretty-print the XML output; boolean, defaults to False
        :rtype: stream passed in or an instance of :class:`cStringIO.StringIO`
        """
        if stream is None:
            string_mode = True
            stream = cStringIO.StringIO()
        else:
            string_mode = False

        # NOTE: etree c14n doesn't seem to like fedora info: URIs
        #self.dom_node.getroottree().write_c14n(stream)
        stream.write(etree.tostring(self.dom_node.getroottree(), encoding='UTF-8', pretty_print=pretty))

        if string_mode:
            data = stream.getvalue()
            stream.close()
            return data
        
        return stream

    def is_valid(self):
        """Determine if the current document is schema-valid according to the
        configured XSD Schema associated with this instance of :class:`XmlObject`.

        :rtype: boolean
        :raises: Exception if no XSD schema is defined for this XmlObject instance
        """
        if self.xmlschema is not None:
            return self.xmlschema.validate(self.dom_node)
        else:
            raise Exception('No XSD schema is defined, cannot validate document')

    def validation_errors(self):
        """
        Retrieve any validation errors that occured during schema validation
        done via :meth:`is_valid`.
        
        :returns: a list of :class:`lxml.etree._LogEntry` instances
        :raises: Exception if no XSD schema is defined for this XmlObject instance
        """
        if self.xmlschema is not None:
            return self.xmlschema.error_log
        else:
            raise Exception('No XSD schema is defined, cannot return validation errors')


def _get_xmlparser(xmlclass=XmlObject, validate=False):
    """Initialize an instance of :class:`lxml.etree.XMLParser` with appropriate
    settings for validation.  If validation is requested and the specified
    instance of :class:`XmlObject` has an XSD_SCHEMA defined, that will be used.
    Otherwise, uses DTD validation.
    """
    if validate:
        if hasattr(xmlclass, 'XSD_SCHEMA') and xmlclass.XSD_SCHEMA is not None:
            if xmlclass.xmlschema is not None:
                # if the schema is already loaded, use that
                xmlschema = xmlclass.xmlschema
            else:         # otherwise, load the schema
                xmlschema = loadSchema(xmlclass.XSD_SCHEMA)
            opts = {'schema': xmlschema}
        else:
            # if configured XmlObject does not have a schema defined, assume DTD validation
            opts = {'dtd_validation': True}
    
    else:
        # if validation is not requested, no parser options are needed
        opts = {}

    return etree.XMLParser(**opts)

def load_xmlobject_from_string(string, xmlclass=XmlObject, validate=False):
    """Initialize an XmlObject from a string.

    If an xmlclass is specified, construct an instance of that class instead
    of :class:`~eulcore.xmlmap.XmlObject`. It should be a subclass of XmlObject.
    The constructor will be passed a single DOM node.

    If validation is requested and the specified subclass of :class:`XmlObject`
    has an XSD_SCHEMA defined, the parser will be configured to validate against
    the specified schema.  Otherwise, the parser will be configured to use DTD
    validation, and expect a Doctype declaration in the xml content.

    :param string: xml content to be loaded, as a string
    :param xmlclass: subclass of :class:`~eulcore.xmlmap.XmlObject` to initialize
    :param validate: boolean, enable validation; defaults to false
    :rtype: instance of :class:`~eulcore.xmlmap.XmlObject` requested
    """
    parser = _get_xmlparser(xmlclass=xmlclass, validate=validate)
    element = etree.fromstring(string, parser)
    return xmlclass(element)


def load_xmlobject_from_file(filename, xmlclass=XmlObject, validate=False):
    """Initialize an XmlObject from a file.

    See :meth:`load_xmlobject_from_string` for more details; behaves exactly the
    same, and accepts the same parameters, except that it takes a filename
    instead of a string.

    :param filename: name of the file that should be loaded as an xmlobject.
        :meth:`etree.lxml.parse` will accept a file name/path, a file object, a
        file-like object, or an HTTP or FTP url, however file path and URL are
        recommended, as they are generally faster for lxml to handle.    
    """
    parser = _get_xmlparser(xmlclass=xmlclass, validate=validate)

    tree = etree.parse(filename, parser)
    return xmlclass(tree.getroot())

# Import these for backward compatibility. Should consider deprecating these
# and asking new code to pull them from descriptor
from eulcore.xmlmap.fields import *
