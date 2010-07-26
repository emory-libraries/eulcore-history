#!/usr/bin/env python

import tempfile
import unittest

import eulcore.xmlmap.core as xmlmap
from testcore import main

class TestFields(unittest.TestCase):
    FIXTURE_TEXT = '''
        <foo id='a' xmlns:ex='http://example.com/'>
            <bar>
                <baz>42</baz>
            </bar>
            <bar>
                <baz>13</baz>
            </bar>
            <empty_field/>
            <boolean>
                    <text1>yes</text1>
                    <text2>no</text2>
                    <num1>1</num1>
                    <num2>0</num2>
            </boolean>
            <spacey>           this text
        needs to be
                normalized
            </spacey>
        </foo>
    '''

    namespaces = {'ex' : 'http://example.com/'}

    def setUp(self):
        # parseString wants a url. let's give it a proper one.
        url = '%s#%s.%s' % (__file__, self.__class__.__name__, 'FIXTURE_TEXT')

        self.fixture = xmlmap.parseString(self.FIXTURE_TEXT, url)

    def testInvalidXpath(self):
        self.assertRaises(Exception, xmlmap.StringField, '["')
        
    def testNodeField(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.StringField('baz')

        class TestObject(xmlmap.XmlObject):
            child = xmlmap.NodeField('bar[1]', TestSubobject)
            missing = xmlmap.NodeField('missing', TestSubobject)

        obj = TestObject(self.fixture)
        self.assertEqual(obj.child.val, '42')
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

        # test instantiate on get hack
        class GetTestObject(xmlmap.XmlObject):
            missing = xmlmap.NodeField('missing', TestSubobject, instantiate_on_get=True)
        obj = GetTestObject(self.fixture)
        self.assert_(isinstance(obj.missing, TestSubobject),
            "non-existent nodefield is created on get when 'instantiate_on_get' flag is set")

    def testNodeListField(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.IntegerField('baz')

        class TestObject(xmlmap.XmlObject):
            children = xmlmap.NodeListField('bar', TestSubobject)
            missing = xmlmap.NodeListField('missing', TestSubobject)

        obj = TestObject(self.fixture)
        child_vals = [ child.val for child in obj.children ]
        self.assertEqual(child_vals, [42, 13])
        self.assertEqual(obj.missing, [])

    def testStringField(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.StringField('bar[1]/baz')
            empty = xmlmap.StringField('empty_field')
            missing = xmlmap.StringField('missing')
            missing_ns = xmlmap.StringField('ex:missing')
            missing_att = xmlmap.StringField('@missing')
            missing_att_ns = xmlmap.StringField('@ex:missing')
            sub_missing = xmlmap.StringField('bar[1]/missing')
            multilevel_missing = xmlmap.StringField('missing_parent/missing_child')
            mixed = xmlmap.StringField('bar[1]')
            id = xmlmap.StringField('@id')
            spacey = xmlmap.StringField('spacey')
            normal_spacey = xmlmap.StringField('spacey', normalize=True)

        obj = TestObject(self.fixture)
        self.assertEqual(obj.val, '42')
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

        # access normalized and non-normalized versions of string field
        self.assertNotEqual("this text needs to be normalized", obj.spacey)
        self.assertEqual("this text needs to be normalized", obj.normal_spacey)

        # set an existing string value
        obj.val = "forty-two"
        # check that new value is set in the node
        self.assertEqual(obj.node.xpath('string(bar[1]/baz)'), "forty-two")
        # check that new value is accessible via descriptor        
        self.assertEqual(obj.val, 'forty-two')

        # set an attribute
        obj.id = 'z'
        # check that new value is set in the node
        self.assertEqual(obj.node.xpath('string(@id)'), "z")
        # check that new value is accessible via descriptor
        self.assertEqual(obj.id, 'z')

        # set value in an empty node
        obj.empty = "full"
        self.assertEqual(obj.node.xpath('string(empty_field)'), "full")
        # check that new value is accessible via descriptor
        self.assertEqual(obj.empty, 'full')

        # set missing fields
        obj.missing = 'not here'
        self.assertEqual(obj.node.xpath('string(missing)'), 'not here')
        # with ns
        obj.missing_ns = 'over there'
        self.assertEqual(obj.node.xpath('string(ex:missing)', namespaces=self.namespaces),
                    'over there')
        # in attrib
        obj.missing_att = 'out to pasture'
        self.assertEqual(obj.node.xpath('string(@missing)'), 'out to pasture')
        # in attrib with ns
        obj.missing_att_ns = "can't find me!"
        self.assertEqual(obj.node.xpath('string(@ex:missing)',
                        namespaces=self.namespaces), "can't find me!")
        # in subelement
        obj.sub_missing = 'pining (for the fjords)'
        self.assertEqual(obj.node.xpath('string(bar/missing)'), 'pining (for the fjords)')

        # in subelement which is itself missing
        obj.multilevel_missing = 'so, so gone'
        self.assertEqual(obj.node.xpath('string(missing_parent/missing_child)'), 'so, so gone')

        # attempting to set a node that contains non-text nodes - error
        self.assertRaises(Exception, obj.__setattr__, "mixed", "whoops")

    def testStringListField(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.StringListField('bar/baz')
            missing = xmlmap.StringListField('missing')
            spacey = xmlmap.StringListField('spacey', normalize=True)

        obj = TestObject(self.fixture)
        self.assertEqual(obj.vals, ['42', '13'])
        self.assertEqual(obj.missing, [])

        # access normalized string list field
        self.assertEqual("this text needs to be normalized", obj.spacey[0])


    def testIntegerField(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.IntegerField('bar[2]/baz')
            missing = xmlmap.IntegerField('missing')

        obj = TestObject(self.fixture)
        self.assertEqual(obj.val, 13)
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

        # set an integer value
        obj.val = 14
        # check that new value is set in the node
        self.assertEqual(obj.node.xpath('number(bar[2]/baz)'), 14)
        # check that new value is accessible via descriptor
        self.assertEqual(obj.val, 14)


    def testIntegerListField(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.IntegerListField('bar/baz')
            missing = xmlmap.IntegerListField('missing')

        obj = TestObject(self.fixture)
        self.assertEqual(obj.vals, [42, 13])
        self.assertEqual(obj.missing, [])

    def testItemField(self):
        class TestObject(xmlmap.XmlObject):
            letter = xmlmap.ItemField('substring(bar/baz, 1, 1)')
            missing = xmlmap.ItemField('missing')

        obj = TestObject(self.fixture)
        self.assertEqual(obj.letter, '4')
        self.assertEqual(obj.missing, None)

    def testBooleanField(self):        
        class TestObject(xmlmap.XmlObject):
            txt_bool1 = xmlmap.SimpleBooleanField('boolean/text1', 'yes', 'no')
            txt_bool2 = xmlmap.SimpleBooleanField('boolean/text2', 'yes', 'no')
            num_bool1 = xmlmap.SimpleBooleanField('boolean/num1', 1, 0)
            num_bool2 = xmlmap.SimpleBooleanField('boolean/num2', 1, 0)
            opt_elem_bool = xmlmap.SimpleBooleanField('boolean/opt', 'yes', None)
            opt_attr_bool = xmlmap.SimpleBooleanField('boolean/@opt', 'yes', None)

        #obj = TestObject(self.fixture.documentElement)
        obj = TestObject(self.fixture)
        self.assertEqual(obj.txt_bool1, True)
        self.assertEqual(obj.txt_bool2, False)
        self.assertEqual(obj.num_bool1, True)
        self.assertEqual(obj.num_bool2, False)
        self.assertEqual(obj.opt_elem_bool, False)
        self.assertEqual(obj.opt_attr_bool, False)

        # set text boolean
        obj.txt_bool1 = False
        # check that new value is set in the node
        self.assertEqual(obj.node.xpath('string(boolean/text1)'), 'no')
        # check that new value is accessible via descriptor
        self.assertEqual(obj.txt_bool1, False)

        # set numeric boolean
        obj.num_bool1 = False
        # check for new new value in the node and via descriptor
        self.assertEqual(obj.node.xpath('number(boolean/num1)'), 0)
        self.assertEqual(obj.num_bool1, False)

        # set optional element boolean
        obj.opt_elem_bool = True
        self.assertEqual(obj.node.xpath('string(boolean/opt)'), 'yes')
        self.assertEqual(obj.opt_elem_bool, True)
        obj.opt_elem_bool = False
        self.assertEqual(obj.node.xpath('count(boolean/opt)'), 0)
        self.assertEqual(obj.opt_elem_bool, False)

        # set optional attribute boolean
        obj.opt_attr_bool = True
        self.assertEqual(obj.node.xpath('string(boolean/@opt)'), 'yes')
        self.assertEqual(obj.opt_attr_bool, True)
        obj.opt_attr_bool = False
        self.assertEqual(obj.node.xpath('count(boolean/@opt)'), 0)
        self.assertEqual(obj.opt_attr_bool, False)


    # FIXME: DateField and DateListField are hacked together. Until we
    #   work up some proper parsing and good testing for them, they should
    #   be considered untested and undocumented features.


    def testSchemaField(self):
        # very simple xsd schema and valid/invalid xml based on the one from lxml docs:
        #   http://codespeak.net/lxml/validation.html#xmlschema
        xsd = '''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <xsd:element name="a" type="AType"/>
            <xsd:complexType name="AType">
                <xsd:sequence>
                    <xsd:element name="b" type="BType" />
                </xsd:sequence>
            </xsd:complexType>
            <xsd:simpleType name="BType">
                <xsd:restriction base="xsd:string">
                    <xsd:enumeration value="c"/>
                    <xsd:enumeration value="d"/>
                    <xsd:enumeration value="e"/>
                </xsd:restriction>
            </xsd:simpleType>
        </xsd:schema>
        '''
        FILE = tempfile.NamedTemporaryFile(mode="w")
        FILE.write(xsd)
        FILE.flush()

        valid_xml = '<a><b>some text</b></a>'

        class TestSchemaObject(xmlmap.XmlObject):
            XSD_SCHEMA = FILE.name
            txt = xmlmap.SchemaField('/a/b', 'BType')

        valid = xmlmap.load_xmlobject_from_string(valid_xml, TestSchemaObject)
        self.assertEqual('some text', valid.txt, 'schema field value is accessible as text')
        self.assert_(isinstance(valid._fields['txt'], xmlmap.StringField),
                'txt SchemaField with base string in schema initialized as StringField')
        self.assertEqual(['c', 'd', 'e'], valid._fields['txt'].choices,
                'txt SchemaField has choices based on restriction enumeration in schema')

        FILE.close()

    def testPredicatedSetting(self):
        class TestObject(xmlmap.XmlObject):
            attr_pred = xmlmap.StringField('pred[@a="foo"]')
            layered_pred = xmlmap.StringField('pred[@a="foo"]/pred[@b="bar"]')
            nested_pred = xmlmap.StringField('pred[pred[@a="foo"]]/val')

        obj = TestObject(self.fixture)

        obj.attr_pred = 'test'
        self.assertEqual(obj.node.xpath('string(pred[@a="foo"])'), 'test')

        obj.layered_pred = 'test'
        self.assertEqual(obj.node.xpath('string(pred[@a="foo"]/pred[@b="bar"])'), 'test')

        obj.nested_pred = 'test'
        self.assertEqual(obj.node.xpath('string(pred[pred[@a="foo"]]/val)'), 'test')


class TestNodeList(unittest.TestCase):
    FIXTURE_TEXT = '''
        <foo>
            <baz>forty-two</baz>
            <baz>thirteen</baz>
            <bar>42</bar>
            <bar>13</bar>
            <l>a</l>
            <l>b</l>
            <l>a</l>
            <l>3</l>
            <l>c</l>
            <l>a</l>
            <l>7</l>
            <l>b</l>
            <l>11</l>
            <l>a</l>
            <l>y</l>
        </foo>
    '''
    
    def setUp(self):
        class ListTestObject(xmlmap.XmlObject):
            str = xmlmap.StringListField('baz')
            int = xmlmap.IntegerListField('bar')
            letters = xmlmap.StringListField('l')
            empty = xmlmap.StringListField('missing')

        # parseString wants a url. let's give it a proper one.
        url = '%s#%s.%s' % (__file__, self.__class__.__name__, 'FIXTURE_TEXT')

        self.fixture = xmlmap.parseString(self.FIXTURE_TEXT, url)
        self.obj = ListTestObject(self.fixture)

    def test_index_checking(self):
        self.assertRaises(TypeError, self.obj.str.__getitem__, 'a')
        self.assertRaises(AssertionError, self.obj.str.__getitem__, slice(0, 10))
        self.assertRaises(TypeError, self.obj.str.__setitem__, 'a', 'val')
        self.assertRaises(AssertionError, self.obj.str.__setitem__, slice(0, 10), ['val'])
        self.assertRaises(TypeError, self.obj.str.__delitem__, 'a')
        self.assertRaises(AssertionError, self.obj.str.__delitem__, slice(0, 10))

    def test_set(self):           
        # set string values
        string_list = self.obj.str
        # - existing nodes in the xml
        new_val = 'twenty-four'
        self.obj.str[0] = new_val
        self.assertEqual(new_val, self.obj.str[0],
            'set value of existing node (position 0) in StringListField - expected %s, got %s' % \
            (new_val, self.obj.str[0]))
        new_val = 'seven'
        string_list[1] = new_val
        self.assertEqual(new_val, string_list[1],
            'set value of existing node (position 1) in StringListField - expected %s, got %s' % \
            (new_val, string_list[1]))
        # - new value for a node at the end of the list - node should be created
        new_val = 'eleventy-one'
        string_list[2] = new_val
        self.assertEqual(new_val, string_list[2],
            'set value of new node (position 2) in StringListField - expected %s, got %s' % \
            (new_val, string_list[2]))
        # - beyond end of current list
        self.assertRaises(IndexError, string_list.__setitem__, 4, 'foo')

        # integer values
        int_list = self.obj.int
        # - existing nodes in the xml
        new_val = 24
        int_list[0] = new_val
        self.assertEqual(new_val, int_list[0],
            'set value of existing node (position 0) in IntegerListField - expected %d, got %d' % \
            (new_val, int_list[0]))
        new_val = 7
        int_list[1] = new_val
        self.assertEqual(new_val, int_list[1],
            'set value of existing node (position 1) in IntegerListField - expected %d, got %d' % \
            (new_val, int_list[1]))
        # - a new value for a node at the end of the list - node should be created
        new_val = 111
        int_list[2] = new_val
        self.assertEqual(new_val, int_list[2],
            'set value of new node (position 2) in IntegerListField - expected %d, got %d' % \
            (new_val, int_list[2]))
        # - beyond end of current list
        self.assertRaises(IndexError, int_list.__setitem__, 4, 23)

        # list with no current members
        self.obj.empty[0] = 'foo'
        self.assertEqual(1, len(self.obj.empty),
            "length of empty list after setting at index 0 should be 1, got %d" % \
            len(self.obj.empty))
        self.assertEqual('foo', self.obj.empty[0])

    def test_del(self):
        # first element
        del(self.obj.str[0])
        self.assertEqual(1, len(self.obj.str),
            "StringListField length should be 1 after deletion, got %d" % len(self.obj.str))
        self.assertEqual('thirteen', self.obj.str[0])

        # second/last element
        int_list = self.obj.int
        del(int_list[1])
        self.assertEqual(1, len(int_list),
            "IntegerListField length should be 1 after deletion, got %d" % len(self.obj.str))

        # out of range
        self.assertRaises(IndexError, int_list.__delitem__, 4)
        self.assertRaises(IndexError, self.obj.empty.__delitem__, 0)

    def test_count(self):
        self.assertEqual(4, self.obj.letters.count('a'))
        self.assertEqual(2, self.obj.letters.count('b'))
        self.assertEqual(0, self.obj.letters.count('z'))
        
        self.assertEqual(0, self.obj.empty.count('z'))

    def test_append(self):
        self.obj.str.append('la')
        self.assertEqual(3, len(self.obj.str),
            "length of StringListField is 3 after appending value")
        self.assertEqual('la', self.obj.str[2])

        int_list = self.obj.int
        int_list.append(9)
        self.assertEqual(3, len(int_list),
            "length of IntegerListField is 3 after appending value")
        self.assertEqual(9, int_list[2])

        # list with no current members
        self.obj.empty.append('foo')
        self.assertEqual(1, len(self.obj.empty),
            "length of empty list after setting appending should be 1, got %d" % \
            len(self.obj.empty))
        self.assertEqual('foo', self.obj.empty[0])

    def test_index(self):
        letters = self.obj.letters
        self.assertEqual(0, letters.index('a'))
        self.assertEqual(1, letters.index('b'))
        self.assertEqual(3, letters.index('3'))

        # not in list
        self.assertRaises(ValueError, letters.index, 'foo')
        self.assertRaises(ValueError, self.obj.empty.index, 'foo')

    def test_remove(self):
        letters = self.obj.letters
        letters.remove('a')
        self.assertNotEqual('a', letters[0],
            "first letter is no longer 'a' after removing 'a'")
        self.assertEqual(1, letters.index('a'),
            "index for 'a' is 1 after removing 'a' - expected 1, got %d" % letters.index('a'))

        # not in list
        self.assertRaises(ValueError, letters.remove, 'foo')
        self.assertRaises(ValueError, self.obj.empty.remove, 'foo')

    def test_pop(self):
        last = self.obj.letters.pop()
        self.assertEqual('y', last,
            "pop with no index returned last letter in list - expected 'y', got '%s'" % last)
        self.assert_('y' not in self.obj.letters,
            "'y' not in stringlistfield after popping last element")

        first = self.obj.letters.pop(0)
        self.assertEqual('a', first,
            "pop with index 0 returned first letter in list - expected 'a', got '%s'" % first)
        self.assertNotEqual('a', self.obj.letters[0],
            "first letter is no longer 'a' after pop index 0")

        # out of range
        self.assertRaises(IndexError, self.obj.empty.pop, 0)
        self.assertRaises(IndexError, self.obj.empty.pop)

    def test_extend(self):
        letters = self.obj.letters
        letters.extend(['w', 'd', '40'])
        self.assert_('w' in letters, 'value in extend list is now in StringList')
        self.assert_('d' in letters, 'value in extend list is now in StringList')
        self.assertEqual('40', letters[len(letters) - 1],
            'last value in extend list is now last element StringList')

        # extend an empty list
        new_list = ['a', 'b', 'c']
        self.obj.empty.extend(new_list)
        self.assertEqual(new_list, self.obj.empty)

    def test_insert(self):
        letters = self.obj.letters
        orig_letters = list(letters.data)   # copy original letters for comparison
        # insert somewhere in the middle
        letters.insert(2, 'q')
        self.assertEqual('q', letters[2],
            "letters[2] should be 'q' after inserting 'q' at 2, got '%s'" % letters[2])
        self.assertEqual(len(orig_letters)+1, len(letters),
            "length of letters should increase by 1 after insert; expected %d, got length %d" \
                % (len(orig_letters)+1, len(letters) ))
        self.assertEqual(orig_letters[2], letters[3],
            "original 3rd letter should be 4th letter after insert; expected '%s', got '%s'" % \
                (orig_letters[2], letters[3]))

        # insert at beginning
        letters.insert(0, 'z')
        self.assertEqual('z', letters[0],
            "letters[0] should be 'z' after inserting 'z' at 0, got '%s'" % letters[0])
        self.assertEqual(len(orig_letters)+2, len(letters),
            "length of letters should increase by 2 after 2nd insert; expected %d, got length %d" \
                % (len(orig_letters)+2, len(letters) ))
        self.assertEqual(orig_letters[0], letters[1],
            "original first letter should be 2nd letter after insert; expected '%s', got '%s'" % \
                (orig_letters[0], letters[1]))

        # 'insert' at the end
        letters.insert(len(letters), '99')
        self.assertEqual('99', letters[-1],
            "last item in letters should be '99' after inserting at end; got '%s'" % letters[-1])

        # out of range
        self.assertRaises(IndexError, letters.insert, 99, 'bar')

        # insert in empty list
        self.obj.empty.insert(0, 'z')
        self.assertEqual('z', self.obj.empty[0],
            "empty[0] should be 'z' after inserting 'z' at 0, got '%s'" % self.obj.empty[0])
        self.assertEqual(1, len(self.obj.empty))


if __name__ == '__main__':
    main()
