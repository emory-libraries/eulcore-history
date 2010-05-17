from datetime import datetime
from Ft.Xml.XPath import Compile, Evaluate
from Ft.Xml.XPath.ParsedNodeTest import LocalNameTest, QualifiedNameTest
from Ft.Xml.XPath.ParsedRelativeLocationPath import ParsedRelativeLocationPath
from Ft.Xml.XPath.ParsedStep import ParsedStep

__all__ = [
    'StringField', 'StringListField',
    'IntegerField', 'IntegerListField',
    'NodeField', 'NodeListField',
    'ItemField', 'SimpleBooleanField'
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
        return self.manager.get(self._xpath, node, context, self.mapper.to_python)

    def set_for_node(self, node, context, value):
        return self.manager.set(self._xpath, node, context, self.mapper.to_xml, value)
        
# data mappers to translate between identified xml nodes and Python values

class Mapper(object):
    # generic mapper to_xml function
    def to_xml(self, value):
        return unicode(value)

class StringMapper(Mapper):
    XPATH = Compile('string()')
    def to_python(self, node):
        return node.xpath(self.XPATH)
       
class NumberMapper(Mapper):
    XPATH = Compile('number()')
    def to_python(self, node):
        return node.xpath(self.XPATH)

class SimpleBooleanMapper(Mapper):
    XPATH = Compile('string()')
    def __init__(self, true, false):
        self.true = true
        self.false = false
        
    def to_python(self, node):
        value = node.xpath(self.XPATH)     
        if value == str(self.true):
            return True
        if value == str(self.false):
            return False        
        # what happens if it is neither of these?
        raise Exception("Boolean field value '%s' is neither '%s' nor '%s'" % (value, self.true, self.false))
        

    def to_xml(self, value):
        if value:
            return str(self.true)
        else:
            return str(self.false)

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

    def to_xml(self, dt):
        # NOTE: untested!  this is probably close to what we need, but should be tested
        return unicode(dt.isoformat())

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
        match = self.find_xml_node(xpath, node, context)
        if match:
            return to_python(match)

    def set(self, xpath, node, context, to_xml, value):
        match = self.find_xml_node(xpath, node, context)
        if not match:
            match = self.create_xml_node(xpath, node, context)
            # create_xml_node() throws an exception on failure

        return self.set_in_xml(match, to_xml(value))

    def find_xml_node(self, xpath, node, context):
        matches = Evaluate(xpath, node, context)
        if matches:
            return matches[0]

    def create_xml_node(self, xpath, node, context):
        effective_xpath = xpath  # use copy so error reporting can use orig

        # the cases we can create:

        # relative paths if the parent exists:
        if isinstance(effective_xpath, ParsedRelativeLocationPath):
            parent_xpath = effective_xpath._left
            parent_nodeset = parent_xpath.evaluate(context)
            if len(parent_nodeset) != 1:
                msg = ("Missing element for '%s', and node creation is " + \
                       "supported only when parent xpath '%s' evaluates " + \
                       "to a single node. Instead, it evaluates to %d.") % \
                       (repr(xpath), repr(parent_xpath), len(parent_nodeset))
                raise Exception(msg)

            # otherwise, we found the parent.
            effective_xpath = effective_xpath._right
            node = parent_nodeset[0]

        # and if the last part of the path is a simple, unpredicated child
        # or attribute
        if isinstance(effective_xpath, ParsedStep):
            if effective_xpath._predicates is None:
                if repr(effective_xpath._axis) == 'child':
                    return self.create_child_node(effective_xpath, node, context)
                if repr(effective_xpath._axis) == 'attribute':
                    return self.create_attribute_node(effective_xpath, node, context)

        # anything else, throw an exception:
        msg = ("Missing element for '%s', and node creation is supported " + \
               "only for simple child and attribute nodes.") % (repr(xpath),)
        raise Exception(msg)

    def create_child_node(self, xpath, node, context):
        ns_uri, node_name = self._get_name_parts(xpath._nodeTest)
        doc = node.ownerDocument
        new_node = doc.createElementNS(ns_uri, node_name)
        node.appendChild(new_node)
        return new_node

    def create_attribute_node(self, xpath, node, context):
        ns_uri, node_name = self._get_name_parts(xpath._nodeTest)
        doc = node.ownerDocument
        new_node = doc.createAttributeNS(ns_uri, node_name)
        node.setAttributeNodeNS(new_node)
        return new_node

    def _get_name_parts(self, node_name_test):
        node_name = repr(node_name_test)
        if isinstance(node_name_test, LocalNameTest):
            ns_uri = None
        elif isinstance(node_name_test, QualifiedNameTest):
            prefix = node_name_test._prefix
            ns_uri = context.processorNss.get(prefix, None)
            # we could throw an exception here if ns_uri wasn't found, but
            # for now assume the user knows what he's doing...
        return ns_uri, node_name

    def set_in_xml(self, node, val):
        if node.nodeType == node.ATTRIBUTE_NODE:
            node.value = val
        else:
            # put all text nodes into a single node so it can be replaced all at once
            node.normalize()
            if node.hasChildNodes():
                if len(node.childNodes) == 1 and node.firstChild.nodeType == node.TEXT_NODE:
                    # can only set value if there is only one child node and it is a text node
                    node.firstChild.data = val
                else:   # child nodes, but not single text node
                    raise Exception("Cannot set string value - not a text node!")
            else:   # no child nodes - create and append new text node
                node.appendChild(node.ownerDocument.createTextNode(val))


class NodeListManager(object):
    def get(self, xpath, node, context, to_python):
        matches = Evaluate(xpath, node, context)
        return [ to_python(match) for match in matches ]

# finished field classes mixing a manager and a mapper

class StringField(Field):

    """Map an XPath expression to a single Python string. If the XPath
    expression evaluates to an empty NodeList, a StringField evaluates to
    `None`.

    Supports setting values for attributes, empty nodes, or text-only nodes.
    """

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
    `None`.

    Supports setting values for attributes, empty nodes, or text-only nodes.
    """

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

class SimpleBooleanField(Field):

    """Map an XPath expression to a Python boolean.  Constructor takes additional
    parameter of true, false values for comparison and setting in xml.  This only
    handles simple boolean that can be read and set via string comparison.

    Supports setting values for attributes, empty nodes, or text-only nodes.
    """

    def __init__(self, xpath, true, false):
        super(SimpleBooleanField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = SimpleBooleanMapper(true, false))


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
    NodeField evaluates to `None`.
    
    Normally a ``NodeField``'s ``node_class`` is a class. As a special
    exception, it may be the string ``"self"``, in which case it recursively
    refers to objects of its containing :class:`XmlObject` class.
    """

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
    NodeListField evaluates to an empty list.
    
    Normally a ``NodeListField``'s ``node_class`` is a class. As a special
    exception, it may be the string ``"self"``, in which case it recursively
    refers to objects of its containing :class:`XmlObject` class.
    """

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
