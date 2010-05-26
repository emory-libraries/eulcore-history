from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker
# NOTE: using 4suite xpath to dynamically create nodes in the dom for
from Ft.Xml.XPath import Compile #, Evaluate
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
        #self._xpath = Compile(xpath)
        self._xpath = xpath
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
    XPATH = etree.XPath('string()')
    def to_python(self, node):
        if isinstance(node, etree._ElementStringResult):
            return node
        return self.XPATH(node)
       
class NumberMapper(Mapper):
    XPATH = etree.XPath('number()')
    def to_python(self, node):
        if isinstance(node, etree._ElementStringResult):
            return int(node)     # FIXME: not equivalent to xpath number()...
        return self.XPATH(node)

class SimpleBooleanMapper(Mapper):
    XPATH = etree.XPath('string()')
    def __init__(self, true, false):
        self.true = true
        self.false = false
        
    def to_python(self, node):
        if isinstance(node, etree._ElementStringResult):
            value = node
        else:
            value = self.XPATH(node)
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
    XPATH = etree.XPath('string()')
    def to_python(self, node):
        if isinstance(node, etree._ElementStringResult):
            rep = node
        else:
            rep = self.XPATH(node)
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

# managers to map operations to either a single identified dom node or a
# list of them

class SingleNodeManager(object):
    def get(self, xpath, node, context, to_python):
        match = self.find_xml_node(xpath, node, context)
        if match is not None:
            return to_python(match)

    def set(self, xpath, node, context, to_xml, value):
        match = self.find_xml_node(xpath, node, context)
        if match == None:
            match = self.create_xml_node(xpath, node, context)
            # create_xml_node() throws an exception on failure

        return self.set_in_xml(match, to_xml(value), xpath, context)

    def find_xml_node(self, xpath, node, context):
        #matches = Evaluate(xpath, node, context)
        matches = node.xpath(xpath, **context)
        if matches:
            return matches[0]

    def create_xml_node(self, xpath, node, context):
        effective_xpath = Compile(xpath)  # use copy so error reporting can use orig

        # the cases we can create:

        # relative paths if the parent exists:
        if isinstance(effective_xpath, ParsedRelativeLocationPath):
            node, effective_xpath = \
                self._find_parent_node(effective_xpath, node, context)

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

    def _find_parent_node(self, xpath, node, context):
        parent_xpath = xpath._left
        parent_nodeset = node.xpath(repr(parent_xpath))        
        if len(parent_nodeset) != 1:
            msg = ("Missing element for '%s', and node creation is " + \
                   "supported only when parent xpath '%s' evaluates " + \
                   "to a single node. Instead, it evaluates to %d.") % \
                   (repr(xpath), repr(parent_xpath), len(parent_nodeset))
            raise Exception(msg)

        # otherwise, we found the parent.
        return parent_nodeset[0], xpath._right

    def create_child_node(self, xpath, node, context):
        ns_uri, node_name, prefix = self._get_name_parts(xpath._nodeTest, context)        
        opts = {}
        if 'namespaces' in context:
            opts['nsmap'] = context['namespaces']
        E = ElementMaker(namespace=ns_uri, **opts)
        new_node = E(node_name)
        node.append(new_node)
        return new_node

    def create_attribute_node(self, xpath, node, context):
        ns_uri, node_name, prefix = self._get_name_parts(xpath._nodeTest, context)        
        nsmap = {}
        xp_node_name = node_name
        if prefix:
            xp_node_name = '%s:%s' % (prefix, node_name)
            node_name = '{%s}%s' % (ns_uri, node_name)            
            nsmap = {prefix: ns_uri}
        # create an empty attribute node so we can set it normally via set_in_xml
        node.set(node_name, '')
        # find via xpath so a 'smart' string can be returned
        result = node.xpath('@%s' % (xp_node_name), namespaces=nsmap)        
        return result[0]

    def _get_name_parts(self, node_name_test, context):
        node_name = repr(node_name_test)
        if isinstance(node_name_test, LocalNameTest):
            ns_uri = None
            prefix = None
        elif isinstance(node_name_test, QualifiedNameTest):
            prefix = node_name_test._prefix
            if 'namespaces' in context:
                ns_uri = context['namespaces'][prefix]            
            #ns_uri = context.processorNss.get(prefix, None)
            else:
                ns_uri = None
            node_name = node_name_test._localName
            # we could throw an exception here if ns_uri wasn't found, but
            # for now assume the user knows what he's doing...        
        return ns_uri, node_name, prefix

    def set_in_xml(self, node, val, xpath, context):
        if isinstance(node, etree._Element):
            if not list(node):      # no child elements
                node.text = val
            else:                 
                raise Exception("Cannot set string value - not a text node!")
        else:
            # by default, etree returns a "smart" string for attribute result;
            # get attribute name from xpath and set on parent node
            attribute = xpath[xpath.rindex('@') + 1:]
            if ':' in attribute:
                prefix, localname = attribute.split(':')                
                attribute = '{%s}%s' % (context['namespaces'][prefix], localname)
            node.getparent().set(attribute, val)


class NodeListManager(object):
    def get(self, xpath, node, context, to_python):        
        matches = node.xpath(xpath, **context) 
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
