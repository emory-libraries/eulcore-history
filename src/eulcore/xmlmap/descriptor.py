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
        if obj is None:
            return self

        nodes = Evaluate(self._xpath, obj.dom_node, obj.context)
        if nodes:
            node = nodes[0]
            return self.convert_node(node)


class XPathListDescriptor(object):
    def __init__(self, xpath):
        self.xpath = xpath  # xpath string
        self._xpath = Compile(xpath) # compiled xpath for actual use

    def __get__(self, obj, objtype):
        if obj is None:
            return self

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

    """Map an XPath expression to a single :class:`XmlObject` subclass
    instance. If the XPath expression evaluates to an empty NodeList, an
    XPathNode descriptor evaluates to `None`."""

    def __init__(self, xpath, node_class):
        XPathItemDescriptor.__init__(self, xpath)
        NodeMapper.__init__(self, node_class)


class XPathNodeList(XPathListDescriptor, NodeMapper):

    """Map an XPath expression to a list of :class:`XmlObject` subclass
    instances. If the XPath expression evalues to an empty NodeList, an
    XPathNodeList descriptor evaluates to an empty list."""

    def __init__(self, xpath, node_class):
        XPathListDescriptor.__init__(self, xpath)
        NodeMapper.__init__(self, node_class)
        

class XPathString(XPathItemDescriptor, StringMapper):
    """Map an XPath expression to a single Python string. If the XPath
    expression evaluates to an empty NodeList, an XPathString descriptor
    evaluates to `None`."""

class XPathStringList(XPathListDescriptor, StringMapper):
    """Map an XPath expression to a list of Python strings. If the XPath
    expression evaluates to an empty NodeList, an XPathStringList desriptor
    evaluates to an empty list."""

class XPathInteger(XPathItemDescriptor, NumberMapper):
    """Map an XPath expression to a single Python integer. If the XPath
    expression evaluates to an empty NodeList, an XPathInteger descriptor
    evaluates to `None`."""

class XPathIntegerList(XPathListDescriptor, NumberMapper):
    """Map an XPath expression to a list of Python integers. If the XPath
    expression evaluates to an empty NodeList, an XPathIntegerList
    descriptor evaluates to an empty list."""

class XPathDate(XPathItemDescriptor, DateMapper):
    """Map an XPath expression to a single Python `datetime.datetime`. If
    the XPath expression evaluates to an empty NodeList, an XPathDate
    descriptor evaluates to `None`.

    .. WARNING::
       XPathDate processing is minimal, undocumented, and liable to change.
       It is not part of any official release. Use it at your own risk.
    """

class XPathDateList(XPathListDescriptor, DateMapper):
    """Map an XPath expression to a list of Python `datetime.datetime`
    objects. If the XPath expression evaluates to an empty NodeList, an
    XPathDateList descriptor evaluates to an empty list.

    .. WARNING::
       XPathDateList processing is minimal, undocumented, and liable to
       change. It is not part of any official release. Use it at your own
       risk.
    """
    pass

class XPathItem(XPathItemDescriptor, NullMapper):
    """Access the results of an XPath expression directly. This descriptor
    does no conversion on the result of evaluating the XPath expression."""
