from Ft.Xml.XPath import Compile, Evaluate
from datetime import datetime

__all__ = [
    'XPathNode', 'XPathNodeList',
    'XPathString', 'XPathStringList',
    'XPathInteger', 'XPathIntegerList',
    'XPathItem',
# NOTE: XPathDate and XPathDateList are undertested and underdocumented. If
#   you really need them, you should import them explicitly. Or even better,
#   flesh them out so they can be properly released.
]

# base classes for single-item and list descriptors

class XPathItemDescriptor(object):
    def __init__(self, xpath):
        self.xpath = xpath  # xpath string
        self._xpath = Compile(xpath) # compiled xpath for actual use

    def __get__(self, obj, objtype):
        nodes = Evaluate(self._xpath, obj.dom_node, obj.context)
        if nodes:
            node = nodes[0]
            return self.convert_node(node)


class XPathListDescriptor(object):
    def __init__(self, xpath):
        self.xpath = xpath  # xpath string
        self._xpath = Compile(xpath) # compiled xpath for actual use

    def __get__(self, obj, objtype):
        nodes = Evaluate(self._xpath, obj.dom_node, obj.context)
        return [ self.convert_node(node) for node in nodes ]


# mappers to translate between identified xml nodes and Python values

class StringMapper(object):
    def convert_node(self, node):
        return node.xpath('string()')

class NumberMapper(object):
    def convert_node(self, node):
        return int(node.xpath('number()'))

class DateMapper(object):
    def convert_node(self, node):
        rep = node.xpath('string()')
        if rep.endswith('Z'): # strip Z
            rep = rep[:-1]
        if rep[-6] in '+-': # strip tz
            rep = rep[:-6]
        dt = datetime.strptime(rep, '%Y-%m-%dT%H:%M:%S')
        return dt

# do no conversion at all - e.g., if xpath returns a string instead of a node
class NullMapper(object):
    def convert_node(self, node):
        return node

class NodeMapper(object):
    def __init__(self, node_class):
        self.node_class = node_class

    def convert_node(self, node):
        return self.node_class(node)


# finished descriptor classes mixing a base with a mapping strategy

class XPathNode(XPathItemDescriptor, NodeMapper):
    def __init__(self, xpath, node_class):
        XPathItemDescriptor.__init__(self, xpath)
        NodeMapper.__init__(self, node_class)


class XPathNodeList(XPathListDescriptor, NodeMapper):
    def __init__(self, xpath, node_class):
        XPathListDescriptor.__init__(self, xpath)
        NodeMapper.__init__(self, node_class)
        

class XPathString(XPathItemDescriptor, StringMapper):
    pass

class XPathStringList(XPathListDescriptor, StringMapper):
    pass

class XPathInteger(XPathItemDescriptor, NumberMapper):
    pass

class XPathIntegerList(XPathListDescriptor, NumberMapper):
    pass

class XPathDate(XPathItemDescriptor, DateMapper):
    pass

class XPathDateList(XPathListDescriptor, DateMapper):
    pass

class XPathItem(XPathItemDescriptor, NullMapper):
    pass
