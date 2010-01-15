from Ft.Xml.Domlette import NonvalidatingReader
from Ft.Xml.XPath.Context import Context
from Ft.Xml.XPath import Compile, Evaluate
from datetime import datetime
from Ft.Lib import Uri

parseUri = NonvalidatingReader.parseUri
parseString = NonvalidatingReader.parseString

class XmlObject(object):
    def __init__(self, dom_node, context=None):
        self.dom_node = dom_node
        self.context = context or Context(dom_node, 
            processorNss=dict([(n.localName, n.value) for n in dom_node.xpathNamespaces]))

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

#    file_uri = Uri.OsPathToUri('spam.xml')
#doc = NonvalidatingReader.parseUri(file_uri)


class XPathDescriptor(object):
    def __init__(self, xpath):
        self.xpath = Compile(xpath)

    def __get__(self, obj, objtype):
        nodes = Evaluate(self.xpath, obj.dom_node, obj.context)
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


class XPathDate(XPathDescriptor):
    def parse_date(self, rep):
        if rep.endswith('Z'): # strip Z
            rep = rep[:-1]
        if rep[-6] in '+-': # strip tz
            rep = rep[:-6]
        dt = datetime.strptime(rep, '%Y-%m-%dT%H:%M:%S')
        return dt

    def convert_node(self, node):
        rep = node.xpath('string()')
        return self.parse_date(rep)

    def convert_nodelist(self, nodes):
        if nodes:
            # better hope there's only one
            return nodes[0]
