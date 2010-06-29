#!/usr/bin/env python

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

        #obj = TestObject(self.fixture.documentElement)
        obj = TestObject(self.fixture)
        self.assertEqual(obj.txt_bool1, True)
        self.assertEqual(obj.txt_bool2, False)
        self.assertEqual(obj.num_bool1, True)
        self.assertEqual(obj.num_bool2, False)

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



    # FIXME: DateField and DateListField are hacked together. Until we
    #   work up some proper parsing and good testing for them, they should
    #   be considered untested and undocumented features.


if __name__ == '__main__':
    main()
