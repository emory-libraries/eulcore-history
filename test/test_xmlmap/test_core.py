#!/usr/bin/env python

import unittest
import tempfile

import eulcore.xmlmap.core as xmlmap
from testcore import main

class TestXsl(unittest.TestCase):
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
    # simple xsl for testing xslTransform - converts bar/baz to just baz
    FIXTURE_XSL = '''<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
        <xsl:template match="bar">
            <xsl:apply-templates select="baz"/>
            </xsl:template>

        <xsl:template match="@*|node()">
            <xsl:copy>
                <xsl:apply-templates select="@*|node()"/>
            </xsl:copy>
        </xsl:template>

    </xsl:stylesheet>'''
    
    def setUp(self):
        # parseString wants a url. let's give it a proper one.
        url = '%s#%s.%s' % (__file__, self.__class__.__name__, 'FIXTURE_TEXT')

        self.fixture = xmlmap.parseString(self.FIXTURE_TEXT, url)

    def test_xslTransform(self):
        class TestObject(xmlmap.XmlObject):
            bar_baz = xmlmap.XPathString('bar[1]/baz')
            nobar_baz = xmlmap.XPathString('baz[1]')

        # xsl in string
        obj = TestObject(self.fixture.documentElement)
        result = obj.xslTransform(xsl=self.FIXTURE_XSL)
        newobj = xmlmap.load_xmlobject_from_string(result, TestObject)
        self.assertEqual('42', newobj.nobar_baz)
        self.assertEqual(None, newobj.bar_baz)

        # xsl in file
        self.FILE = tempfile.NamedTemporaryFile(mode="w")
        self.FILE.write(self.FIXTURE_XSL)
        self.FILE.flush()

        obj = TestObject(self.fixture.documentElement)
        result = obj.xslTransform(filename=self.FILE.name)
        newobj = xmlmap.load_xmlobject_from_string(result, TestObject)
        self.assertEqual('42', newobj.nobar_baz)
        self.assertEqual(None, newobj.bar_baz)

        self.FILE.close()

        # not yet tested: xsl with parameters


# NOTE: using TestXsl fixture text for the init tests

class TestXmlObjectStringInit(unittest.TestCase):

    def test_load_from_string(self):
        """Test using shortcut to initialize XmlObject from string"""
        obj = xmlmap.load_xmlobject_from_string(TestXsl.FIXTURE_TEXT)
        self.assert_(isinstance(obj, xmlmap.XmlObject))

    def test_load_from_string_with_classname(self):
        """Test using shortcut to initialize named XmlObject class from string"""
        
        class TestObject(xmlmap.XmlObject):
            pass
        
        obj = xmlmap.load_xmlobject_from_string(TestXsl.FIXTURE_TEXT, TestObject)
        self.assert_(isinstance(obj, TestObject))


class TestXmlObjectFileInit(unittest.TestCase):
    
    def setUp(self):
        self.FILE = tempfile.NamedTemporaryFile(mode="w")
        self.FILE.write(TestXsl.FIXTURE_TEXT)
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


class TestGetXmlObjectXPath(unittest.TestCase):    

    def test_getXmlObjectXPath(self):

        class TestSubSubObject(xmlmap.XmlObject):
            fo = xmlmap.XPathString('fi/fum')

        class TestSubObject(xmlmap.XmlObject):
            field = xmlmap.XPathString('fighters')
            fi = xmlmap.XPathNode('fee/fo', TestSubSubObject)

        class TestObject(xmlmap.XmlObject):
            val = xmlmap.XPathString('bar[1]/baz')
            sub = xmlmap.XPathNode('foo', TestSubObject)

        class TestChildObject(TestObject):
            # inherited xpaths should be accessible
            subval = xmlmap.XPathString('foo/bar')

        self.assertEqual("bar[1]/baz", xmlmap.getXmlObjectXPath(TestObject, 'val'))
        self.assertEqual("foo/bar", xmlmap.getXmlObjectXPath(TestChildObject, 'subval'))
        self.assertEqual("bar[1]/baz", xmlmap.getXmlObjectXPath(TestChildObject, 'val'))
        self.assertEqual("foo/fighters", xmlmap.getXmlObjectXPath(TestObject, 'sub__field'))
        self.assertEqual("foo/fee/fo/fi/fum", xmlmap.getXmlObjectXPath(TestObject, 'sub__fi__fo'))
        # attempting to get a path for something that isn't a child (fi not under field)
        # FIXME: more specific exception?
        self.assertRaises(Exception, xmlmap.getXmlObjectXPath, TestObject, 'sub__field__fi')



if __name__ == '__main__':
    main()
