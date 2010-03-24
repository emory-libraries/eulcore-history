from datetime import datetime
from Ft.Xml.XPath import Compile, Evaluate

__all__ = [
    'StringField', 'StringListField',
    'IntegerField', 'IntegerListField',
    'NodeField', 'NodeListField',
    'ItemField',
# NOTE: DateField and DateListField are undertested and underdocumented. If
#   you really need them, you should import them explicitly. Or even better,
#   flesh them out so they can be properly released.
]

# base class for all fields

class Field(object):
    def __init__(self, xpath, manager, mapper):
        self.xpath = xpath
        self._xpath = Compile(xpath)
        self.manager = manager
        self.mapper = mapper

    def get_for_node(self, node, context):
        return self.manager.get(self.xpath, node, context, self.mapper.to_python)

# data mappers to translate between identified xml nodes and Python values

class StringMapper(object):
    XPATH = Compile('string()')
    def to_python(self, node):
        return node.xpath(self.XPATH)

class NumberMapper(object):
    XPATH = Compile('number()')
    def to_python(self, node):
        return node.xpath(self.XPATH)

class DateMapper(object):
    XPATH = Compile('string()')
    def to_python(self, node):
        rep = node.xpath(self.XPATH)
        if rep.endswith('Z'): # strip Z
            rep = rep[:-1]
        if rep[-6] in '+-': # strip tz
            rep = rep[:-6]
        dt = datetime.strptime(rep, '%Y-%m-%dT%H:%M:%S')
        return dt

class NullMapper(object):
    def to_python(self, node):
        return node

class NodeMapper(object):
    def __init__(self, node_class):
        self.node_class = node_class

    def to_python(self, node):
        return self.node_class(node)

# managers to map operations to either a single idenfitied dom node or a
# list of them

class SingleNodeManager(object):
    def get(self, xpath, node, context, to_python):
        matches = Evaluate(xpath, node, context)
        if matches:
            return to_python(matches[0])

class NodeListManager(object):
    def get(self, xpath, node, context, to_python):
        matches = Evaluate(xpath, node, context)
        return [ to_python(match) for match in matches ]

# finished field classes mixing a manager and a mapper

class StringField(Field):

    """Map an XPath expression to a single Python string. If the XPath
    expression evaluates to an empty NodeList, a StringField evaluates to
    `None`."""

    def __init__(self, xpath):
        super(StringField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = StringMapper())

class StringListField(Field):

    """Map an XPath expression to a list of Python strings. If the XPath
    expression evaluates to an empty NodeList, a StringListField evaluates to
    an empty list."""

    def __init__(self, xpath):
        super(StringListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = StringMapper())

class IntegerField(Field):

    """Map an XPath expression to a single Python integer. If the XPath
    expression evaluates to an empty NodeList, an IntegerField evaluates to
    `None`."""

    def __init__(self, xpath):
        super(IntegerField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = NumberMapper())

class IntegerListField(Field):

    """Map an XPath expression to a list of Python integers. If the XPath
    expression evaluates to an empty NodeList, an IntegerListField evaluates to
    an empty list."""

    def __init__(self, xpath):
        super(IntegerListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = NumberMapper())

class DateField(Field):

    """Map an XPath expression to a single Python `datetime.datetime`. If
    the XPath expression evaluates to an empty NodeList, a DateField evaluates
    to `None`.

    .. WARNING::
       DateField processing is minimal, undocumented, and liable to change.
       It is not part of any official release. Use it at your own risk.
    """

    def __init__(self, xpath):
        super(DateField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = DateMapper())

class DateListField(Field):

    """Map an XPath expression to a list of Python `datetime.datetime`
    objects. If the XPath expression evaluates to an empty NodeList, a
    DateListField evaluates to an empty list.

    .. WARNING::
       DateListField processing is minimal, undocumented, and liable to
       change. It is not part of any official release. Use it at your own
       risk.
    """

    def __init__(self, xpath):
        super(DateListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = DateMapper())

class NodeField(Field):

    """Map an XPath expression to a single :class:`XmlObject` subclass
    instance. If the XPath expression evaluates to an empty NodeList, a
    NodeField evaluates to `None`."""

    def __init__(self, xpath, node_class):
        super(NodeField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = NodeMapper(node_class))

    def _get_node_class(self):
        return self.mapper.node_class
    def _set_node_class(self, val):
        self.mapper.node_class = val
    node_class = property(_get_node_class, _set_node_class)

class NodeListField(Field):

    """Map an XPath expression to a list of :class:`XmlObject` subclass
    instances. If the XPath expression evalues to an empty NodeList, a
    NodeListField evaluates to an empty list."""

    def __init__(self, xpath, node_class):
        super(NodeListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = NodeMapper(node_class))

    def _get_node_class(self):
        return self.mapper.node_class
    def _set_node_class(self, val):
        self.mapper.node_class = val
    node_class = property(_get_node_class, _set_node_class)

class ItemField(Field):

    """Access the results of an XPath expression directly. An ItemField does no
    conversion on the result of evaluating the XPath expression."""

    def __init__(self, xpath):
        super(ItemField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = NullMapper())
