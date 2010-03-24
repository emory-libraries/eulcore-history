#!/usr/bin/env python

import unittest

import eulcore.xmlmap.core as xmlmap
from testcore import main

class TestFields(unittest.TestCase):
    FIXTURE_TEXT = '''
        <foo>
            <bar>
                <baz>42</baz>
            </bar>
            <bar>
                <baz>13</baz>
            </bar>
        </foo>
    '''

    def setUp(self):
        # parseString wants a url. let's give it a proper one.
        url = '%s#%s.%s' % (__file__, self.__class__.__name__, 'FIXTURE_TEXT')

        self.fixture = xmlmap.parseString(self.FIXTURE_TEXT, url)

    def testNodeField(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.StringField('baz')

        class TestObject(xmlmap.XmlObject):
            child = xmlmap.NodeField('bar[1]', TestSubobject)
            missing = xmlmap.NodeField('missing', TestSubobject)

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.child.val, '42')
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

    def testNodeListField(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.IntegerField('baz')

        class TestObject(xmlmap.XmlObject):
            children = xmlmap.NodeListField('bar', TestSubobject)
            missing = xmlmap.NodeListField('missing', TestSubobject)

        obj = TestObject(self.fixture.documentElement)
        child_vals = [ child.val for child in obj.children ]
        self.assertEqual(child_vals, [42, 13])
        self.assertEqual(obj.missing, [])

    def testStringField(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.StringField('bar[1]/baz')
            missing = xmlmap.StringField('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, '42')
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

    def testStringListField(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.StringListField('bar/baz')
            missing = xmlmap.StringListField('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.vals, ['42', '13'])
        self.assertEqual(obj.missing, [])

    def testIntegerField(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.IntegerField('bar[2]/baz')
            missing = xmlmap.IntegerField('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, 13)
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

    def testIntegerListField(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.IntegerListField('bar/baz')
            missing = xmlmap.IntegerListField('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.vals, [42, 13])
        self.assertEqual(obj.missing, [])

    def testItemField(self):
        class TestObject(xmlmap.XmlObject):
            letter = xmlmap.ItemField('substring(bar/baz, 1, 1)')
            missing = xmlmap.ItemField('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.letter, '4')
        self.assertEqual(obj.missing, None)


    # FIXME: DateField and DateListField are hacked together. Until we
    #   work up some proper parsing and good testing for them, they should
    #   be considered untested and undocumented features.


if __name__ == '__main__':
    main()
