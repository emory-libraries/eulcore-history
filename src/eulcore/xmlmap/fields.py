# file xmlmap/fields.py
# 
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from datetime import datetime
from lxml import etree
from lxml.builder import ElementMaker
from eulcore.xpath import ast, parse, serialize
from types import ListType, FloatType

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
        return self.manager.get(self.xpath, node, context, self.mapper, self.parsed_xpath)

    def set_for_node(self, node, context, value):
        return self.manager.set(self.xpath, self.parsed_xpath, node, context, self.mapper, value)


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
        if node is None:
            return None
        if isinstance(node, basestring):
            return node
        return self.XPATH(node)
       
class NumberMapper(Mapper):
    XPATH = etree.XPath('number()')
    def to_python(self, node):
        if node is None:
            return None
        #xpath functions such as count
        #return a float and need to  converted to int
        if isinstance(node, basestring) or isinstance(node, FloatType):
            return int(node)     # FIXME: not equivalent to xpath number()...
        return self.XPATH(node)

class SimpleBooleanMapper(Mapper):
    XPATH = etree.XPath('string()')
    def __init__(self, true, false):
        self.true = true
        self.false = false
        
    def to_python(self, node):
        if node is None and \
                self.false is None:
            return False

        if isinstance(node, basestring):
            value = node
        else:
            value = self.XPATH(node)
        if value == str(self.true):
            return True
        if self.false is not None and \
                value == str(self.false):
            return False        
        # what happens if it is neither of these?
        raise Exception("Boolean field value '%s' is neither '%s' nor '%s'" % (value, self.true, self.false))

    def to_xml(self, value):
        if value:
            return str(self.true)
        elif self.false is not None:
            return str(self.false)
        else:
            return None


class DateMapper(object):
    XPATH = etree.XPath('string()')
    def to_python(self, node):
        if node is None:
            return None
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
        if node is None:
            return None
        return self.node_class(node)


# internal xml utility functions for use by managers

def _find_terminal_step(xast):
    if isinstance(xast, ast.Step):
        return xast
    elif isinstance(xast, ast.BinaryExpression):
        if xast.op in ('/', '//'):
            return _find_terminal_step(xast.right)
    return None

def _find_xml_node(xpath, node, context):
    #In some cases the this will return a value not a node
    matches = node.xpath(xpath, **context)
    if matches and isinstance(matches, ListType):
        return matches[0]
    elif matches:
        return matches

def _create_xml_node(xast, node, context, insert_index=None):
    if isinstance(xast, ast.Step):
        if isinstance(xast.node_test, ast.NameTest):
            # check the predicates (if any) to verify they're constructable
            for pred in xast.predicates:
                if not _predicate_is_constructible(pred):
                    msg = ("Missing element for '%s', and node creation is " +
                           "supported only for simple child and attribute " +
                           "nodes with simple predicates.") % (serialize(xast),)
                    raise Exception(msg)

            # create the node itself
            if xast.axis in (None, 'child'):
                new_node = _create_child_node(node, context, xast, insert_index)
            elif xast.axis in ('@', 'attribute'):
                new_node = _create_attribute_node(node, context, xast)

            # and create any nodes necessary for the predicates
            for pred in xast.predicates:
                _construct_predicate(pred, new_node, context)

            return new_node
    elif isinstance(xast, ast.BinaryExpression):
        if xast.op == '/':
            left_xpath = serialize(xast.left)
            left_node = _find_xml_node(left_xpath, node, context)
            if left_node is None:
                left_node = _create_xml_node(xast.left, node, context)
            return _create_xml_node(xast.right, left_node, context)

    # anything else, throw an exception:
    msg = ("Missing element for '%s', and node creation is supported " + \
           "only for simple child and attribute nodes.") % (serialize(xast),)
    raise Exception(msg)

def _create_child_node(node, context, step, insert_index=None):
    opts = {}
    ns_uri = None
    if 'namespaces' in context:
        opts['nsmap'] = context['namespaces']
        if step.node_test.prefix:
            ns_uri = context['namespaces'][step.node_test.prefix]
    E = ElementMaker(namespace=ns_uri, **opts)
    new_node = E(step.node_test.name)
    if insert_index is not None:
        node.insert(insert_index, new_node)
    else:
        node.append(new_node)
    return new_node

def _create_attribute_node(node, context, step):
    node_name, node_xpath, nsmap = _get_attribute_name(step, context)
    # create an empty attribute node
    node.set(node_name, '')
    # find via xpath so a 'smart' string can be returned and set normally
    result = node.xpath(node_xpath, namespaces=nsmap)
    return result[0]

def _predicate_is_constructible(pred):
    if isinstance(pred, ast.Step):
        # only child and attribute for now
        if pred.axis not in (None, 'child', '@', 'attribute'):
            return False
        # no node tests for now: only name tests
        if not isinstance(pred.node_test, ast.NameTest):
            return False
        # only constructible if its own predicates are
        if any((not _predicate_is_constructible(sub_pred)
                for sub_pred in pred.predicates)):
            return False
    elif isinstance(pred, ast.BinaryExpression):
        if pred.op == '/':
            # path expressions are constructible if each side is
            if not _predicate_is_constructible(pred.left):
                return False
            if not _predicate_is_constructible(pred.right):
                return False
        elif pred.op == '=':
            # = expressions are constructible for now only if the left side
            # is constructible and the right side is a literal or variable
            if not _predicate_is_constructible(pred.left):
                return False
            if not isinstance(pred.right,
                    (int, long, basestring, ast.VariableReference)):
                return False

    # otherwise, i guess we're ok
    return True

def _construct_predicate(xast, node, context):
    if isinstance(xast, ast.Step):
        return _create_xml_node(xast, node, context)
    elif isinstance(xast, ast.BinaryExpression):
        if xast.op == '/':
            left_leaf = _construct_predicate(xast.left, node, context)
            right_node = _construct_predicate(xast.right, left_node, context)
            return right_node
        elif xast.op == '=':
            left_leaf = _construct_predicate(xast.left, node, context)
            step = _find_terminal_step(xast.left)
            if isinstance(xast.right, ast.VariableReference):
                name = xast.right.name
                ctxval = context.get(name, None)
                if ctxval is None:
                    ctxval = context[name[1]]
                xvalue = str(ctxval)
            else:
                xvalue = str(xast.right)
            _set_in_xml(left_leaf, xvalue, context, step)
            return left_leaf

def _set_in_xml(node, val, context, step):
    if isinstance(node, etree._Element):
        if not list(node):      # no child elements
            node.text = val
        else:                 
            raise Exception("Cannot set string value - not a text node!")
    elif hasattr(node, 'getparent'):
        # by default, etree returns a "smart" string for attribute result;
        # determine attribute name and set on parent node
        attribute, node_xpath, nsmap = _get_attribute_name(step, context)
        node.getparent().set(attribute, val)

def _remove_xml(xast, node, context):
    if isinstance(xast, ast.Step):
        if isinstance(xast.node_test, ast.NameTest):
            if xast.axis in (None, 'child'):
                _remove_child_node(node, context, xast)
            elif xast.axis in ('@', 'attribute'):
                _remove_attribute_node(node, context, xast)
    elif isinstance(xast, ast.BinaryExpression):
        if xast.op == '/':
            left_xpath = serialize(xast.left)
            left_node = _find_xml_node(left_xpath, node, context)
            if left_node is not None:
                _remove_xml(xast.right, left_node, context)
    
def _remove_child_node(node, context, xast):
    xpath = serialize(xast)
    child = _find_xml_node(xpath, node, context)
    if child is not None:
        node.remove(child)

def _remove_attribute_node(node, context, xast):
    node_name, node_xpath, nsmap = _get_attribute_name(xast, context)
    del node.attrib[node_name]

def _get_attribute_name(step, context):
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


# managers to map operations to either a single identified node or a
# list of them

class SingleNodeManager(object):

    def __init__(self, instantiate_on_get=False):
        self.instantiate_on_get = instantiate_on_get

    def get(self, xpath, node, context, mapper, xast):
        match = _find_xml_node(xpath, node, context)
        if match is None and self.instantiate_on_get:
            return mapper.to_python(_create_xml_node(xast, node, context))
        # else, non-None match, or not instantiate
        return mapper.to_python(match)

    def set(self, xpath, xast, node, context, mapper, value):
        xvalue = mapper.to_xml(value)
        match = _find_xml_node(xpath, node, context)

        if xvalue is None:
            # match must be None. if it exists, delete it.
            if match is not None:
                _remove_xml(xast, node, context)
        else:
            if match is None:
                match = _create_xml_node(xast, node, context)
            # terminal (rightmost) step informs how we update the xml
            step = _find_terminal_step(xast)
            _set_in_xml(match, xvalue, context, step)

class NodeList(object):
    """Custom List-like object to handle ListFields like :class:`IntegerListField`,
    :class:`StringListField`, and :class:`NodeListField`, which allows for getting,
    setting, and deleting list members.  :class:`NodeList` should **not** be
    initialized directly, but instead should only be accessed as the return type
    from a ListField.

    Supports common list functions and operators, including the following: len();
    **in**; equal and not equal comparison to standard python Lists.  Items can
    be retrieved, set, and deleted by index, but slice indexing is not supported.
    Supports the methods that Python documentation indicates should be provided
    by Mutable sequences, with the exceptions of reverse and sort; in the
    particular case of :class:`NodeListField`, it is unclear how a list of 
    :class:`~eulcore.xmlmap.XmlObject` should be sorted, or whether or not such
    a thing would be useful or meaningful for XML content.
    
    When a new element is appended to a :class:`~eulcore.xmlmap.fields.NodeList`,
    it will be added to the XML immediately after the last element in the list.
    In the case of an empty list, the new content will be appended at the end of
    the appropriate XML parent node.  For XML content where element order is important
    for schema validity, extra care may be required when constructing content.
    """
    def __init__(self, xpath, node, context, mapper, xast):
        self.xpath = xpath
        self.node = node
        self.context = context
        self.mapper = mapper
        self.xast = xast

    @property
    def matches(self):
        # current matches from the xml tree
        # NOTE: retrieving from the xml every time rather than caching
        # because the xml document could change, and we want the latest data
        return self.node.xpath(self.xpath, **self.context)

    @property
    def data(self):
        # data in list form - basis for several other list-y functions
        return [ self.mapper.to_python(match) for match in self.matches ]

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self.data)

    def __len__(self):
        return len(self.data)

    def __contains__(self, item):
        return item in self.data

    def __iter__(self):
        for item in self.matches:
            yield self.mapper.to_python(item)

    def __eq__(self, other):
        # FIXME: is any other comparison possible ?
        return self.data == other

    def __ne__(self, other):
        return self.data != other

    def _check_key_type(self, key):
        # check argument type for getitem, setitem, delitem
        if not isinstance(key, (slice, int, long)):
            raise TypeError
        assert not isinstance(key, slice), "Slice indexing is not supported"

    def __getitem__(self, key):
        self._check_key_type(key)
        return self.mapper.to_python(self.matches[key])

    def __setitem__(self, key, value):
        self._check_key_type(key)
        if key == len(self.matches):
            # just after the end of the list - create a new node            
            if len(self.matches):
                # if there are existing nodes, use last element in list
                # to determine where the new node should be created
                last_item = self.matches[-1]
                position = last_item.getparent().index(last_item)
                insert_index = position + 1
            else:
                insert_index = None
            match = _create_xml_node(self.xast, self.node, self.context, insert_index)
        elif key > len(self.matches):
            raise IndexError("Can't set at index %d - out of range" % key )
        else:
            match = self.matches[key]

        if isinstance(self.mapper, NodeMapper):
            # if this is a NodeListField, the value should be an xmlobject
            # replace the indexed node with the node specified
            # NOTE: lxml does not require dom-style import before append/replace
            match.getparent().replace(match, value.node)
        else:       # not a NodeListField - set single-node value in xml
            # terminal (rightmost) step informs how we update the xml
            step = _find_terminal_step(self.xast)
            _set_in_xml(match, self.mapper.to_xml(value), self.context, step)
        
    def __delitem__(self, key):
        self._check_key_type(key)
        if key >= len(self.matches):
            raise IndexError("Can't delete at index %d - out of range" % key )
        
        match = self.matches[key]
        match.getparent().remove(match)

# according to python docs, Mutable sequences should provide the following methods:
# append, count, index, extend, insert, pop, remove, reverse and sort
# NOTE: not implementing sort/reverse at this time; not clear

    def count(self, x):
        "Return the number of times x appears in the list."
        return self.data.count(x)

    def append(self, x):
        "Add an item to the end of the list."
        self[len(self)] = x

    def index(self, x):
        """Return the index in the list of the first item whose value is x,
        or error if there is no such item."""
        return self.data.index(x)

    def remove(self, x):
        """Remove the first item from the list whose value is x,
        or error if there is no such item."""
        del(self[self.index(x)])

    def pop(self, i=None):
        """Remove the item at the given position in the list, and return it.
        If no index is specified, removes and returns the last item in the list."""
        if i is None:
            i = len(self) - 1
        val = self[i]
        del(self[i])
        return val

    def extend(self, list):
        """Extend the list by appending all the items in the given list."""
        for item in list:
            self.append(item)

    def insert(self, i, x):
        """Insert an item (x) at a given position (i)."""
        if i == len(self):  # end of list or empty list: append
            self.append(x)
        elif len(self.matches) > i:
            # create a new xml node at the requested position
            insert_index = self.matches[i].getparent().index(self.matches[i])                        
            _create_xml_node(self.xast, self.node, self.context, insert_index)
            # then use default set logic
            self[i] = x
        else:
            raise IndexError("Can't insert '%s' at index %d - list length is only %d" \
                            % (x, i, len(self)))
        



class NodeListManager(object):
    def get(self, xpath, node, context, mapper, xast):
        return NodeList(xpath, node, context, mapper, xast)

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

    Actual return type is :class:`~eulcore.xmlmap.fields.NodeList`, which can be
    treated like a regular Python list, and includes set and delete functionality.
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
    an empty list.

    Actual return type is :class:`~eulcore.xmlmap.fields.NodeList`, which can be
    treated like a regular Python list, and includes set and delete functionality.
    """

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

    Actual return type is :class:`~eulcore.xmlmap.fields.NodeList`, which can be
    treated like a regular Python list, and includes set and delete functionality.
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

    Actual return type is :class:`~eulcore.xmlmap.fields.NodeList`, which can be
    treated like a regular Python list, and includes set and delete functionality.
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

