#!/usr/bin/env python

from lxml import etree
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
            bar_baz = xmlmap.StringField('bar[1]/baz')
            nobar_baz = xmlmap.StringField('baz[1]')

        # xsl in string
        #obj = TestObject(self.fixture.documentElement)
        obj = TestObject(self.fixture)
        result = obj.xslTransform(xsl=self.FIXTURE_XSL)
        newobj = xmlmap.load_xmlobject_from_string(str(result), TestObject)
        self.assertEqual('42', newobj.nobar_baz)
        self.assertEqual(None, newobj.bar_baz)

        # xsl in file
        self.FILE = tempfile.NamedTemporaryFile(mode="w")
        self.FILE.write(self.FIXTURE_XSL)
        self.FILE.flush()

        #obj = TestObject(self.fixture.documentElement)
        obj = TestObject(self.fixture)
        result = obj.xslTransform(filename=self.FILE.name)
        newobj = xmlmap.load_xmlobject_from_string(str(result), TestObject)
        self.assertEqual('42', newobj.nobar_baz)
        self.assertEqual(None, newobj.bar_baz)

        self.FILE.close()

        # not yet tested: xsl with parameters


# NOTE: using TestXsl fixture text for the init tests

class TestXmlObjectStringInit(unittest.TestCase):
    # example invalid document from 4suite documentation
    INVALID_XML = """<!DOCTYPE a [
  <!ELEMENT a (b, b)>
  <!ELEMENT b EMPTY>
]>
<a><b/><b/><b/></a>"""
    VALID_XML = """<!DOCTYPE a [
  <!ELEMENT a (b, b)>
  <!ELEMENT b EMPTY>
]>
<a><b/><b/></a>"""
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

    def test_load_from_string_with_validation(self):
       
        self.assertRaises(Exception, xmlmap.load_xmlobject_from_string, self.INVALID_XML, validate=True)
        # fixture with no doctype also causes a validation error
        self.assertRaises(Exception, xmlmap.load_xmlobject_from_string,
            TestXsl.FIXTURE_TEXT, validate=True)

        obj = xmlmap.load_xmlobject_from_string(self.VALID_XML)
        self.assert_(isinstance(obj, xmlmap.XmlObject))

        
class TestXmlObjectFileInit(unittest.TestCase):
    
    def setUp(self):
        self.FILE = tempfile.NamedTemporaryFile(mode="w")
        self.FILE.write(TestXsl.FIXTURE_TEXT)
        self.FILE.flush()

        # valid and invalid examples with a simple doctype
        self.VALID = tempfile.NamedTemporaryFile(mode="w")
        self.VALID.write(TestXmlObjectStringInit.VALID_XML)
        self.VALID.flush()

        self.INVALID = tempfile.NamedTemporaryFile(mode="w")
        self.INVALID.write(TestXmlObjectStringInit.INVALID_XML)
        self.INVALID.flush()

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

    def test_load_from_file_with_validation(self):
        # has doctype, but not valid
        self.assertRaises(Exception, xmlmap.load_xmlobject_from_file, self.INVALID.name, validate=True)
        # no doctype
        self.assertRaises(Exception, xmlmap.load_xmlobject_from_file, self.FILE.name, validate=True)
        # doctype, valid
        obj = xmlmap.load_xmlobject_from_file(self.VALID.name, validate=True)
        self.assert_(isinstance(obj, xmlmap.XmlObject))

class TestXmlObject(unittest.TestCase):

    def setUp(self):
        self.obj = xmlmap.load_xmlobject_from_string(TestXsl.FIXTURE_TEXT)
        
    def test__unicode(self):
        u = self.obj.__unicode__()
        self.assert_("42 13" in u)

    def test__string(self):
        self.assertEqual('42 13', self.obj.__string__())

        # convert xml with unicode content
        obj = xmlmap.load_xmlobject_from_string(u'<text>unicode \u2026</text>')
        self.assertEqual('unicode &#8230;', obj.__string__())

    def test_serialize_tostring(self):
        xml_s = self.obj.serialize()        
        self.assert_("<baz>42</baz>" in xml_s)

    def test_serialize_tofile(self):
        FILE = tempfile.TemporaryFile()
        self.obj.serialize(stream=FILE)
        FILE.flush()
        FILE.seek(0)
        self.assert_("<baz>13</baz>" in FILE.read())
        FILE.close()

    def test_isvalid(self):
        # attempting schema-validation on an xmlobject with no schema should raise an exception
        self.assertRaises(Exception, self.obj.schema_valid)

        # generic validation with no schema -- assumed True
        self.assertTrue(self.obj.is_valid())

        # very simple xsd schema and valid/invalid xml taken from lxml docs:
        #   http://codespeak.net/lxml/validation.html#xmlschema
        xsd = '''<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <xsd:element name="a" type="AType"/>
            <xsd:complexType name="AType">
                <xsd:sequence>
                    <xsd:element name="b" type="xsd:string" />
                </xsd:sequence>
            </xsd:complexType>
        </xsd:schema>
        '''
        FILE = tempfile.NamedTemporaryFile(mode="w")
        FILE.write(xsd)
        FILE.flush()

        valid_xml = '<a><b></b></a>'
        invalid_xml = '<a foo="1"><c></c></a>'

        class TestSchemaObject(xmlmap.XmlObject):
            XSD_SCHEMA = FILE.name
        
        valid = xmlmap.load_xmlobject_from_string(valid_xml, TestSchemaObject)
        self.assertTrue(valid.is_valid())
        self.assertTrue(valid.schema_valid())

        invalid = xmlmap.load_xmlobject_from_string(invalid_xml, TestSchemaObject)        
        self.assertFalse(invalid.is_valid())
        invalid.is_valid()
        self.assertEqual(2, len(invalid.validation_errors()))

        # do schema validation at load time
        valid = xmlmap.load_xmlobject_from_string(valid_xml, TestSchemaObject,
            validate=True)
        self.assert_(isinstance(valid, TestSchemaObject))

        self.assertRaises(etree.XMLSyntaxError, xmlmap.load_xmlobject_from_string,
            invalid_xml, TestSchemaObject, validate=True)

        FILE.close()

if __name__ == '__main__':
    main()
