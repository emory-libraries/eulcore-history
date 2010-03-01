from Ft.Lib import Uri
from Ft.Xml.Domlette import NonvalidatingReader
from Ft.Xml.XPath import Compile, Evaluate
from Ft.Xml.XPath.Context import Context
from Ft.Xml.Xslt import Processor
from datetime import datetime

__all__ = [ 'XmlObject', 'parseUri', 'parseString',
    'load_xmlobject_from_string', 'load_xmlobject_from_file' ]

parseUri = NonvalidatingReader.parseUri
parseString = NonvalidatingReader.parseString

class XmlObject(object):

    """A Python object wrapped around an XML DOM node.

    Typical programs will define subclasses of :class:`XmlObject` with
    various descriptor members. Generally they will use
    :func:`load_xmlobject_from_string` and :func:`load_xmlobject_from_file`
    to create instances of these subclasses, though they can be constructed
    directly if more control is necessary.

    In particular, programs can pass an optional
    :class:`Ft.Xml.XPath.Context` argument to the constructor to specify an
    XPath evaluation context with alternate namespace or variable
    definitions. By default, descriptors are evaluated in an XPath context
    containing the namespaces of the wrapped DOM node and no variables.

    """

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

def getXmlObjectXPath(obj, var):
    "Return the xpath string for an xmlmap field that belongs to the specified XmlObject"    
    if var in obj.__dict__:
        return obj.__dict__[var].xpath
    if hasattr(obj, '__bases__'):
        for baseclass in obj.__bases__:
            # FIXME: should this check isinstance of XmlObject ?
            xpath = getXmlObjectXPath(baseclass, var)
            if xpath:
                return xpath


def load_xmlobject_from_string(string, xmlclass=XmlObject):
    """Initialize an XmlObject from a string.

    If an xmlclass is specified, construct an instance of that class instead
    of XmlObject. It should be a subclass of XmlObject. The constructor will
    passed a single DOM node.
    
    """
    # parseString wants a uri, but context doesn't really matter for a string...
    parsed_str= parseString(string, "urn:bogus")
    return xmlclass(parsed_str.documentElement)

def load_xmlobject_from_file(filename, xmlclass=XmlObject):
    """Initialize an XmlObject from a file.

    If an xmlclass is specified, construct an instance of that class instead
    of XmlObject. It should be a subclass of XmlObject. The constructor will
    passed a single DOM node.
    
    """
    file_uri = Uri.OsPathToUri(filename)
    parsed_file = parseUri(file_uri)
    return xmlclass(parsed_file.documentElement)

# Import these for backward compatibility. Should consider deprecating these
# and asking new code to pull them from descriptor
from eulcore.xmlmap.descriptor import *
