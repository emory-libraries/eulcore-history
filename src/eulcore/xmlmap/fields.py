from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker
from eulcore.xpath import ast, parse, serialize

__all__ = [
    'StringField', 'StringListField',
    'IntegerField', 'IntegerListField',
    'NodeField', 'NodeListField',
    'ItemField', 'SimpleBooleanField',
# NOTE: DateField and DateListField are undertested and underdocumented. If
#   you really need them, you should import them explicitly. Or even better,
#   flesh them out so they can be properly released.
    'SchemaField',
]

# base class for all fields

class Field(object):

    # track each time a Field instance is created, to retain order
    creation_counter = 0

    def __init__(self, xpath, manager, mapper):
        # compile xpath in order to catch an invalid xpath at load time
        etree.XPath(xpath)
        # NOTE: not saving compiled xpath because namespaces must be
        # passed in at compile time when evaluating an etree.XPath on a node
        self.xpath = xpath
        self.manager = manager
        self.mapper = mapper

        # pre-parse the xpath for setters, etc
        self.parsed_xpath = parse(xpath)

        # adjust creation counter, save local copy of current count
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def get_for_node(self, node, context):
        return self.manager.get(self.xpath, node, context, self.mapper.to_python, self.parsed_xpath)

    def set_for_node(self, node, context, value):
        return self.manager.set(self.xpath, self.parsed_xpath, node, context, self.mapper.to_xml, value)


# data mappers to translate between identified xml nodes and Python values

class Mapper(object):
    # generic mapper to_xml function
    def to_xml(self, value):
        return unicode(value)

class StringMapper(Mapper):
    XPATH = etree.XPath('string()')
    def __init__(self, normalize=False):
        if normalize:
            self.XPATH = etree.XPath('normalize-space(string())')
        
    def to_python(self, node):
        if isinstance(node, basestring):
            return node
        return self.XPATH(node)
       
class NumberMapper(Mapper):
    XPATH = etree.XPath('number()')
    def to_python(self, node):
        if isinstance(node, basestring):
            return int(node)     # FIXME: not equivalent to xpath number()...
        return self.XPATH(node)

class SimpleBooleanMapper(Mapper):
    XPATH = etree.XPath('string()')
    def __init__(self, true, false):
        self.true = true
        self.false = false
        
    def to_python(self, node):
        if isinstance(node, basestring):
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
        if isinstance(node, basestring):
            rep = node
        else:
            rep = self.XPATH(node)
        if rep.endswith('Z'): # strip Z
            rep = rep[:-1]
        if rep[-6] in '+-': # strip tz
            rep = rep[:-6]
        try:
            dt = datetime.strptime(rep, '%Y-%m-%dT%H:%M:%S')
        except ValueError, v:
            # if initial format fails, attempt to parse with microseconds
            dt = datetime.strptime(rep, '%Y-%m-%dT%H:%M:%S.%f')
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

# managers to map operations to either a single identified node or a
# list of them

class SingleNodeManager(object):

    def __init__(self, instantiate_on_get=False):
        self.instantiate_on_get = instantiate_on_get

    def get(self, xpath, node, context, to_python, xast):
        match = self.find_xml_node(xpath, node, context)
        if match is not None:
            return to_python(match)
        elif self.instantiate_on_get:
            return to_python(self.create_xml_node(xast, node, context))

    def set(self, xpath, xast, node, context, to_xml, value):
        xvalue = to_xml(value)
        match = self.find_xml_node(xpath, node, context)
        terminal_step = None
        if match is None:
            match = self.create_xml_node(xast, node, context)
        # terminal (rightmost) step informs how we update the xml
        step = self.find_terminal_step(xast)
        self.set_in_xml(match, xvalue, context, step)

    def find_terminal_step(self, xast):
        if isinstance(xast, ast.Step):
            return xast
        elif isinstance(xast, ast.BinaryExpression):
            if xast.op in ('/', '//'):
                return self.find_terminal_step(xast.right)
        return None

    def find_xml_node(self, xpath, node, context):
        matches = node.xpath(xpath, **context)
        if matches:
            return matches[0]

    def create_xml_node(self, xast, node, context):
        if isinstance(xast, ast.Step):
            if isinstance(xast.node_test, ast.NameTest) and \
                    len(xast.predicates) == 0:
                if xast.axis in (None, 'child'):
                    return self.create_child_node(node, context, xast)
                elif xast.axis in ('@', 'attribute'):
                    return self.create_attribute_node(node, context, xast)
        elif isinstance(xast, ast.BinaryExpression):
            if xast.op == '/':
                left_xpath = serialize(xast.left)
                left_node = self.find_xml_node(left_xpath, node, context)
                if left_node is None:
                    left_node = self.create_xml_node(xast.left, node, context)
                return self.create_xml_node(xast.right, left_node, context)

        # anything else, throw an exception:
        msg = ("Missing element for '%s', and node creation is supported " + \
               "only for simple child and attribute nodes.") % (serialize(xast),)
        raise Exception(msg)

    def create_child_node(self, node, context, step):
        opts = {}
        ns_uri = None
        if 'namespaces' in context:
            opts['nsmap'] = context['namespaces']
            if step.node_test.prefix:
                ns_uri = context['namespaces'][step.node_test.prefix]
        E = ElementMaker(namespace=ns_uri, **opts)
        new_node = E(step.node_test.name)
        node.append(new_node)
        return new_node

    def create_attribute_node(self, node, context, step):
        node_name, node_xpath, nsmap = self._get_attribute_name(step, context)
        # create an empty attribute node
        node.set(node_name, '')
        # find via xpath so a 'smart' string can be returned and set normally
        result = node.xpath(node_xpath, namespaces=nsmap)
        return result[0]

    def set_in_xml(self, node, val, context, step):
        if isinstance(node, etree._Element):
            if not list(node):      # no child elements
                node.text = val
            else:                 
                raise Exception("Cannot set string value - not a text node!")
        elif hasattr(node, 'getparent'):
            # by default, etree returns a "smart" string for attribute result;
            # determine attribute name and set on parent node
            attribute, node_xpath, nsmap = self._get_attribute_name(step, context)
            node.getparent().set(attribute, val)

    def _get_attribute_name(self, step, context):
        # calculate attribute name, xpath, and nsmap based on node info and context namespaces
        if not step.node_test.prefix:
            nsmap = {}
            ns_uri = None
            node_name = step.node_test.name
            node_xpath = '@%s' % node_name
        else:
            # if node has a prefix, the namespace *should* be defined in context
            if 'namespaces' in context and step.node_test.prefix in context['namespaces']:
                ns_uri = context['namespaces'][step.node_test.prefix]
            else:
                ns_uri = None
                # we could throw an exception here if ns_uri wasn't found, but
                # for now assume the user knows what he's doing...

            node_xpath = '@%s:%s' % (step.node_test.prefix, step.node_test.name)
            node_name = '{%s}%s' % (ns_uri, step.node_test.name)
            nsmap = {step.node_test.prefix: ns_uri}

        return node_name, node_xpath, nsmap
        

class NodeListManager(object):
    def get(self, xpath, node, context, to_python, xast):
        matches = node.xpath(xpath, **context)
        return [ to_python(match) for match in matches ]

# finished field classes mixing a manager and a mapper

class StringField(Field):

    """Map an XPath expression to a single Python string. If the XPath
    expression evaluates to an empty NodeList, a StringField evaluates to
    `None`.

    Takes an optional parameter to indicate that the string contents should have
    whitespace normalized.  By default, does not normalize.

    Takes an optional list of choices to restrict possible values.

    Supports setting values for attributes, empty nodes, or text-only nodes.
    """
    
    def __init__(self, xpath, normalize=False, choices=None):
        self.choices = choices
        # FIXME: handle at a higher level, common to all/more field types?
        #        does choice list need to be checked in the python ?
        super(StringField, self).__init__(xpath,
                manager = SingleNodeManager(),
                mapper = StringMapper(normalize=normalize))

class StringListField(Field):

    """Map an XPath expression to a list of Python strings. If the XPath
    expression evaluates to an empty NodeList, a StringListField evaluates to
    an empty list.


    Takes an optional parameter to indicate that the string contents should have
    whitespace normalized.  By default, does not normalize.

    """
    def __init__(self, xpath, normalize=False):
        super(StringListField, self).__init__(xpath,
                manager = NodeListManager(),
                mapper = StringMapper(normalize=normalize))

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

    Optional ``instantiate_on_get`` flag: set to True if you need a non-existent
    node to be created when the NodeField is accessed.  (Currently needed for
    :class:`eulcore.django.forms.xmlobject.XmlObjectForm` if you want to dynamically
    add missing fields under a NodeField to XML.)
    """

    def __init__(self, xpath, node_class, instantiate_on_get=False):
        super(NodeField, self).__init__(xpath,
                manager = SingleNodeManager(instantiate_on_get=instantiate_on_get),
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

class SchemaField(Field):
    """Schema-based field.  At class definition time, a SchemaField will be
    **replaced** with the appropriate :class:`eulcore.xmlmap.fields.Field` type
    based on the schema type definition.

    Takes an xpath (which will be passed on to the real Field init) and a schema
    type definition name.  If the schema type has enumerated restricted values,
    those will be passed as choices to the Field.

    Currently only supports simple string-based schema types.
    """
    def __init__(self, xpath, schema_type):
        self.xpath = xpath
        self.schema_type = schema_type

    def get_field(self, schema):
        """Get the requested type definition from the schema and return the
        appropriate :class:`~eulcore.xmlmap.fields.Field`.

        :param schema: instance of :class:`eulcore.xmlmap.core.XsdSchema`
        :rtype: :class:`eulcore.xmlmap.fields.Field`
        """
        type = schema.get_type(self.schema_type)
        kwargs = {}
        if type.restricted_values:
            # field has a restriction with enumerated values - pass as choices to field
            kwargs['choices'] = type.restricted_values
        # TODO: possibly also useful to look for pattern restrictions
        
        basetype = type.base_type()
        if basetype == 'string':            
            return StringField(self.xpath, **kwargs)
        else:
            raise Exception("basetype %s is not yet supported by SchemaField" % basetype)

