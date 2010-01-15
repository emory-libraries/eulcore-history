#!/usr/bin/env python

import unittest
import tempfile

import eulcore.xmlmap.core as xmlmap

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
            missing = xmlmap.XPathString('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, '42')
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

    def testIntegerDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            val = xmlmap.XPathInteger('bar[2]/baz')
            missing = xmlmap.XPathInteger('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.val, 13)
        self.assertEqual(obj.missing, None)
        # undefined if >1 matched nodes

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

    def testStringListDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.XPathStringList('bar/baz')
            missing = xmlmap.XPathStringList('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.vals, ['42', '13'])
        self.assertEqual(obj.missing, [])

    def testIntegerListDescriptor(self):
        class TestObject(xmlmap.XmlObject):
            vals = xmlmap.XPathIntegerList('bar/baz')
            missing = xmlmap.XPathIntegerList('missing')

        obj = TestObject(self.fixture.documentElement)
        self.assertEqual(obj.vals, [42, 13])
        self.assertEqual(obj.missing, [])

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


# NOTE: using TestDescriptors fixture text for the init tests

class TestXmlObjectStringInit(unittest.TestCase):

    def test_load_from_string(self):
        """Test using shortcut to initialize XmlObject from string"""
        obj = xmlmap.load_xmlobject_from_string(TestDescriptors.FIXTURE_TEXT)
        self.assert_(isinstance(obj, xmlmap.XmlObject))

    def test_load_from_string_with_classname(self):
        """Test using shortcut to initialize named XmlObject class from string"""
        
        class TestObject(xmlmap.XmlObject):
            pass
        
        obj = xmlmap.load_xmlobject_from_string(TestDescriptors.FIXTURE_TEXT, TestObject)
        self.assert_(isinstance(obj, TestObject))


class TestXmlObjectFileInit(unittest.TestCase):
    
    def setUp(self):
        self.FILE = tempfile.NamedTemporaryFile(mode="w")
        self.FILE.write(TestDescriptors.FIXTURE_TEXT)
        self.FILE.flush()

    def tearDown(self):
        self.FILE.close()
    def test_load_from_file(self):
        """Test using shortcut to initialize XmlObject from a file"""
        obj = xmlmap.load_xmlobject_from_file(self.FILE.name)
        self.assert_(isinstance(obj, xmlmap.XmlObject))

    def test_load_from_file_with_classname(self):
        """Test using shortcut to initialize named XmlObject class from string"""
        
        class TestObject(xmlmap.XmlObject):
            pass
        
        obj = xmlmap.load_xmlobject_from_file(self.FILE.name, TestObject)
        self.assert_(isinstance(obj, TestObject))



if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner)
