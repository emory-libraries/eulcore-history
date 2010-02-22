from Ft.Xml.Domlette import NonvalidatingReader
from Ft.Xml.XPath.Context import Context
from Ft.Xml.XPath import Compile, Evaluate
from Ft.Xml.Xslt import Processor
from datetime import datetime
from Ft.Lib import Uri

parseUri = NonvalidatingReader.parseUri
parseString = NonvalidatingReader.parseString

class XmlObject(object):
    def __init__(self, dom_node, context=None):
        self.dom_node = dom_node
        self.context = context or Context(dom_node, 
            processorNss=dict([(n.localName, n.value) for n in dom_node.xpathNamespaces]))

    def xslTransform(self, filename=None, xsl=None, params={}):
        """Run an xslt transform on the contents of the XmlObject.
           XSLT can be passed as filename or string.
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
    """Convenience function to initialize an XmlObject from a string"""
    # parseString wants a uri, but context doesn't really matter for a string...
    parsed_str= parseString(string, "urn:bogus")
    return xmlclass(parsed_str.documentElement)

def load_xmlobject_from_file(filename, xmlclass=XmlObject):
    """Convenience function to initialize an XmlObject from a file"""
    file_uri = Uri.OsPathToUri(filename)
    parsed_file = parseUri(file_uri)
    return xmlclass(parsed_file.documentElement)

# Import these for backward compatibility. Should consider deprecating these
# and asking new code to pull them from descriptor
from eulcore.xmlmap.descriptor import XPathDate, XPathDateList
from eulcore.xmlmap.descriptor import XPathInteger, XPathIntegerList
from eulcore.xmlmap.descriptor import XPathNode, XPathNodeList
from eulcore.xmlmap.descriptor import XPathString, XPathStringList
