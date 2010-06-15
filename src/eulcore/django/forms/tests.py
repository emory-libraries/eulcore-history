import unittest

from django import forms

from eulcore import xmlmap
from eulcore.django.forms import XmlObjectForm, XmlObjectFormType, xmlobjectform_factory

# test xmlobject and xml content to generate test form

class TestSubobject(xmlmap.XmlObject):
    ROOT_NAME = 'bar'
    val = xmlmap.IntegerField('baz')
    id2 = xmlmap.StringField('@id')

class TestObject(xmlmap.XmlObject):
    ROOT_NAME = 'foo'
    id = xmlmap.StringField('@id')
    int = xmlmap.IntegerField('bar[2]/baz')
    bool = xmlmap.SimpleBooleanField('boolean', 'yes', 'no')
    longtext = xmlmap.StringField('longtext', normalize=True)
    #children = xmlmap.NodeListField('bar', TestSubobject)      # lists not handled yet
    children = xmlmap.NodeField('bar', TestSubobject)

FIXTURE_TEXT = '''
    <foo id='a'>
        <bar id='forty-two'>
            <baz>42</baz>
        </bar>
        <bar>
            <baz>13</baz>
        </bar>
        <boolean>yes</boolean>
        <longtext>here is a bunch of text too long for a text input</longtext>
    </foo>
'''
class TestForm(XmlObjectForm):
    class Meta:
        model = TestObject


class XmlObjectFormTest(unittest.TestCase):

    def setUp(self):
        # instance of form with no test object
        self.new_form = TestForm()
        # instance of form with test object instance
        testobj = xmlmap.load_xmlobject_from_string(FIXTURE_TEXT, TestObject)
        self.update_form = TestForm(testobj)

    def tearDown(self):
        pass

    def test_simple_fields(self):
        # there should be a form field for each simple top-level xmlmap field
        
        # note: currently formobject uses field name for formfield label, but that could change
        formfields = self.new_form.base_fields

        self.assert_('int' in formfields, 'int field is present in form fields')
        self.assert_(isinstance(formfields['int'], forms.IntegerField),
            "xmlmap.IntegerField 'int' initialized as IntegerField")
        expected, got = 'int', formfields['int'].label
        self.assertEqual(expected, got, "form field label should be set to " + \
            "xmlmap field name; expected %s, got %s" % (expected, got))

        self.assert_('id' in formfields, 'id field is present in form fields')
        self.assert_(isinstance(formfields['id'], forms.CharField),
            "xmlmap.StringField 'id' field initialized as CharField")
        expected, got = 'id', formfields['id'].label
        self.assertEqual(expected, got, "form field label should be set to " + \
            "xmlmap field name; expected %s, got %s" % (expected, got))

        self.assert_('bool' in formfields, 'bool field is present in form fields')
        self.assert_(isinstance(formfields['bool'], forms.BooleanField),
            "xmlmap.SimpleBooleanField 'bool' field initialized as BooleanField")
        expected, got = 'bool', formfields['bool'].label
        self.assertEqual(expected, got, "form field label should be set to " + \
            "xmlmap field name; expected %s, got %s" % (expected, got))

    def test_field_value_from_instance(self):
        # when form is initialized from an xmlobject instance, form should 
        # have initial field values be pulled from the xml object
        
        initial_data = self.update_form.initial   # initial values set on BaseForm
        expected, got = 'a', initial_data['id']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'id' should be %s, got %s" % \
            (expected, got))

        expected, got = 13, initial_data['int']
        self.assertEqual(13, initial_data['int'],
           "initial instance-based form value for 'int' should be %s, got %s" % \
            (expected, got))

        expected, got = True, initial_data['bool']
        self.assertEqual(True, initial_data['bool'],
           "initial instance-based form value for 'bool' should be %s, got %s" % \
            (expected, got))

    def test_xmlobjectform_factory(self):
        form = xmlobjectform_factory(TestObject)
        # creates and returns a new form class of type XmlObjectFormType
        self.assert_(isinstance(form, XmlObjectFormType),
            'factory-generated form class is of type XmlObjectFormType')

        expected, got = 'TestObjectXmlObjectForm', form.__name__
        self.assertEqual(expected, got,
            "factory-generated form class has a reasonable name; expected %s, got %s" % \
            (expected, got))
        self.assertEqual(TestObject, form.Meta.model,
            "xmlobject class 'TestObject' correctly set as model in form class Meta")

        # specify particular fields - should be set in form Meta
        form = xmlobjectform_factory(TestObject, fields=['int', 'bool'])        
        self.assert_('int' in form.Meta.fields)
        self.assert_('bool' in form.Meta.fields)
        self.assert_('id' not in form.Meta.fields)

        # exclude particular fields - should be set in form Meta
        form = xmlobjectform_factory(TestObject, exclude=['int', 'bool'])
        self.assert_('int' in form.Meta.exclude)
        self.assert_('bool' in form.Meta.exclude)
        self.assert_('id' not in form.Meta.exclude)

    def test_specified_fields(self):
        # if fields are specified, only they should be listed
        myform = xmlobjectform_factory(TestObject, fields=['int', 'bool'])
        form = myform()
        self.assert_('int' in form.base_fields,
            'int field is present in form fields when specified in field list')
        self.assert_('bool' in form.base_fields,
            'bool field is present in form fields when specified in field list')
        self.assert_('id' not in form.base_fields,
            'id field is not present in form fields when not specified in field list')

    def test_exclude(self):
        # if exclude is specified, those fields should not be listed
        myform = xmlobjectform_factory(TestObject, exclude=['id', 'bool'])
        form = myform()
        self.assert_('int' in form.base_fields,
            'int field is present in form fields when not excluded')
        self.assert_('longtext' in form.base_fields,
            'longtext field is present in form fields when not excluded')
        self.assert_('bool' not in form.base_fields,
            'bool field is not present in form fields when excluded')
        self.assert_('id' not in form.base_fields,
            'id field is not present in form fields when excluded')

    def test_widgets(self):
        # specify custom widget
        class MyForm(XmlObjectForm):
            class Meta:
                model = TestObject
                widgets = {'longtext': forms.Textarea }

        form = MyForm()
        self.assert_(isinstance(form.base_fields['longtext'].widget, forms.Textarea),
            'longtext form field has Textarea widget as specfied in form class Meta')
        self.assert_(isinstance(form.base_fields['id'].widget, forms.TextInput),
            'StringField id form field has default TextInput widget')






