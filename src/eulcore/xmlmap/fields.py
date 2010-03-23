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


class Field(object):
    def __init__(self, xpath, manager, mapper):
        self.xpath = xpath
        self._xpath = Compile(xpath)
        self.manager = manager
        self.mapper = mapper

    def get_for_node(self, node, context):
        return self.manager.get(self.xpath, node, context, self.mapper.to_python)

###

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

###

class SingleNodeManager(object):
    def get(self, xpath, node, context, to_python):
        matches = Evaluate(xpath, node, context)
        if matches:
            return to_python(matches[0])

class NodeListManager(object):
    def get(self, xpath, node, context, to_python):
        matches = Evaluate(xpath, node, context)
        return [ to_python(match) for match in matches ]

###

class StringField(Field):
    def __init__(self, xpath):
        super(StringField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = StringMapper())

class StringListField(Field):
    def __init__(self, xpath):
        super(StringListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = StringMapper())

class IntegerField(Field):
    def __init__(self, xpath):
        super(IntegerField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = NumberMapper())

class IntegerListField(Field):
    def __init__(self, xpath):
        super(IntegerListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = NumberMapper())

class DateField(Field):
    def __init__(self, xpath):
        super(DateField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = DateMapper())

class DateListField(Field):
    def __init__(self, xpath):
        super(DateListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = DateMapper())

class NodeField(Field):
    def __init__(self, xpath, node_class):
        super(NodeField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = NodeMapper(node_class))
        self.node_class = node_class

class NodeListField(Field):
    def __init__(self, xpath, node_class):
        super(NodeListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = NodeMapper(node_class))
        self.node_class = node_class

class ItemField(Field):
    def __init__(self, xpath):
        super(ItemField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = NullMapper())
