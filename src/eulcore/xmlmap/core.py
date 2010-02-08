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

class XPathDescriptor(object):
    def __init__(self, xpath):
        self.xpath = xpath  # xpath string
        self._xpath = Compile(xpath) # compiled xpath for actual use

    def __get__(self, obj, objtype):
        nodes = Evaluate(self._xpath, obj.dom_node, obj.context)
        cnodes = [ self.convert_node(node) for node in nodes ]
        return self.convert_nodelist(cnodes)

    # override for per-node conversions
    def convert_node(self, node):
        return node

    # override for full-nodelist conversions
    def convert_nodelist(self, nodes):
        return nodes


class XPathNode(XPathDescriptor):
    def __init__(self, xpath, node_class):
        XPathDescriptor.__init__(self, xpath)
        self.node_class = node_class

    def convert_node(self, node):
        return self.node_class(node)

    def convert_nodelist(self, nodes):
        if nodes:
            return nodes[0]


class XPathNodeList(XPathDescriptor):
    def __init__(self, xpath, node_class):
        XPathDescriptor.__init__(self, xpath)
        self.node_class = node_class

    def convert_node(self, node):
        return self.node_class(node)
        

class XPathString(XPathDescriptor):
    def convert_node(self, node):
        return node.xpath('string()')

    def convert_nodelist(self, nodes):
        if nodes:
            return ''.join(nodes)


class XPathStringList(XPathDescriptor):
    def convert_node(self, node):
        return node.xpath('string()')


class XPathInteger(XPathDescriptor):
    def convert_node(self, node):
        return int(node.xpath('number()'))

    def convert_nodelist(self, nodes):
        if nodes:
            # better hope there's only one
            return nodes[0]


class XPathIntegerList(XPathDescriptor):
    def convert_node(self, node):
        return int(node.xpath('number()'))


def parse_date(rep):
    if rep.endswith('Z'): # strip Z
        rep = rep[:-1]
    if rep[-6] in '+-': # strip tz
        rep = rep[:-6]
    dt = datetime.strptime(rep, '%Y-%m-%dT%H:%M:%S')
    return dt

class XPathDate(XPathDescriptor):
    def convert_node(self, node):
        rep = node.xpath('string()')
        return parse_date(rep)

    def convert_nodelist(self, nodes):
        if nodes:
            # better hope there's only one
            return nodes[0]

class XPathDateList(XPathDescriptor):
    def convert_node(self, node):
        rep = node.xpath('string()')
        return parse_date(rep)
