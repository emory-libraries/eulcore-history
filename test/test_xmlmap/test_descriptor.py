#!/usr/bin/env python

import unittest

import eulcore.xmlmap.core as xmlmap
from testcore import main

class TestDescriptors(unittest.TestCase):
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

    def testNodeDescriptor(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.XPathString('baz')

        class TestObject(xmlmap.XmlObject):
            child = xmlmap.XPathNode('bar[1]', TestSubobject)
            missing = xmlmap.XPathNode('missing', TestSubobject)

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.child.val, '42')
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

    def testNodeListDescriptor(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.XPathInteger('baz')

        class TestObject(xmlmap.XmlObject):
            children = xmlmap.XPathNodeList('bar', TestSubobject)
            missing = xmlmap.XPathNodeList('missing', TestSubobject)

        obj = TestObject(self.fixture.documentElement)
        child_vals = [ child.val for child in obj.children ]
        self.assertEqual(child_vals, [42, 13])
        self.assertEqual(obj.missing, [])

    def testStringDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.XPathString('bar[1]/baz')
            missing = xmlmap.XPathString('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, '42')
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

    def testStringListDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.XPathStringList('bar/baz')
            missing = xmlmap.XPathStringList('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.vals, ['42', '13'])
        self.assertEqual(obj.missing, [])

    def testIntegerDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.XPathInteger('bar[2]/baz')
            missing = xmlmap.XPathInteger('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, 13)
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

    def testIntegerListDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.XPathIntegerList('bar/baz')
            missing = xmlmap.XPathIntegerList('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.vals, [42, 13])
        self.assertEqual(obj.missing, [])

    # FIXME: XPathDate and XPathDateList are hacked together. Until we
    #   work up some proper parsing and good testing for them, they should
    #   be considered untested and undocumented features.


if __name__ == '__main__':
    main()
