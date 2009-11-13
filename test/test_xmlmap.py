#!/usr/bin/env python

import unittest

from eulcore import xmlmap

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

    def testStringDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.XPathString('bar[1]/baz')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, '42')

    def testIntegerDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.XPathInteger('bar[2]/baz')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, 13)

    def testNodeDescriptor(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.XPathString('baz')

        class TestObject(xmlmap.XmlObject):
            child = xmlmap.XPathNode('bar[1]', TestSubobject)

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.child.val, '42')

    def testStringListDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.XPathStringList('bar/baz')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.vals, ['42', '13'])

    def testNodeListDescriptor(self):
        class TestSubobject(xmlmap.XmlObject):
            val = xmlmap.XPathInteger('baz')

        class TestObject(xmlmap.XmlObject):
            children = xmlmap.XPathNodeList('bar', TestSubobject)

        obj = TestObject(self.fixture.documentElement)
        child_vals = [ child.val for child in obj.children ]
        self.assertEqual(child_vals, [42, 13])


if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner)
