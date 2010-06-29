import unittest

from django import forms

from eulcore import xmlmap
from eulcore.xmlmap.fields import DateField     # not yet supported - testing for errors
from eulcore.django.forms import XmlObjectForm, xmlobjectform_factory
from eulcore.django.forms.xmlobject import XmlObjectFormType


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
    my_opt = xmlmap.StringField('opt', choices=['a', 'b', 'c'])

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

    # sample POST data for testing form update logic (used by multiple tests)
    post_data = {
        'children-id2': 'two',
        'children-val': 2,
        # include base form data so form will be valid
        'longtext': 'completely new text content',
        'int': 21,
        'bool': False,
        'id': 'b',
        'my_opt': 'c',
        }


    def setUp(self):
        # instance of form with no test object
        self.new_form = TestForm()
        # instance of form with test object instance
        self.testobj = xmlmap.load_xmlobject_from_string(FIXTURE_TEXT, TestObject)
        self.update_form = TestForm(instance=self.testobj)

    def tearDown(self):
        pass

    def test_simple_fields(self):
        # there should be a form field for each simple top-level xmlmap field
        
        # note: currently formobject uses field name for formfield label, but that could change
        formfields = self.new_form.base_fields

        self.assert_('int' in formfields, 'int field is present in form fields')
        self.assert_(isinstance(formfields['int'], forms.IntegerField),
            "xmlmap.IntegerField 'int' initialized as IntegerField")
        expected, got = 'Int', formfields['int'].label
        self.assertEqual(expected, got, "form field label should be set to " + \
            "xmlmap field name; expected %s, got %s" % (expected, got))

        self.assert_('id' in formfields, 'id field is present in form fields')
        self.assert_(isinstance(formfields['id'], forms.CharField),
            "xmlmap.StringField 'id' field initialized as CharField")
        expected, got = 'Id', formfields['id'].label
        self.assertEqual(expected, got, "form field label should be set to " + \
            "xmlmap field name; expected %s, got %s" % (expected, got))

        self.assert_('bool' in formfields, 'bool field is present in form fields')
        self.assert_(isinstance(formfields['bool'], forms.BooleanField),
            "xmlmap.SimpleBooleanField 'bool' field initialized as BooleanField")
        expected, got = 'Bool', formfields['bool'].label
        self.assertEqual(expected, got, "form field label should be set to " + \
            "xmlmap field name; expected %s, got %s" % (expected, got))

        # choice field
        self.assert_('my_opt' in formfields, 'my_opt field is present in form fields')
        self.assert_(isinstance(formfields['my_opt'], forms.ChoiceField),
            "xmlmap.StringField 'my_opt' with choices form field initialized as ChoiceField")
        expected, got = 'My Opt', formfields['my_opt'].label
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
        myfields = ['int', 'bool']
        myform = xmlobjectform_factory(TestObject, fields=myfields)
        form = myform()
        self.assert_('int' in form.base_fields,
            'int field is present in form fields when specified in field list')
        self.assert_('bool' in form.base_fields,
            'bool field is present in form fields when specified in field list')
        self.assert_('id' not in form.base_fields,
            'id field is not present in form fields when not specified in field list')

        # form field order should match order in fields list
        self.assertEqual(myfields, form.base_fields.keys())

        # second variant to confirm field order
        myfields = ['longtext', 'int', 'bool']
        myform = xmlobjectform_factory(TestObject, fields=myfields)
        form = myform()
        self.assertEqual(myfields, form.base_fields.keys())

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

    def test_default_field_order(self):
        # form field order should correspond to field order in xmlobject, which is:
        # id, int, bool, longtext, [children]
        field_names = self.update_form.base_fields.keys()
        self.assertEqual('id', field_names[0],
            "first field in xmlobject ('id') is first in form fields")
        self.assertEqual('int', field_names[1],
            "second field in xmlobject ('int') is second in form fields")
        self.assertEqual('bool', field_names[2],
            "third field in xmlobject ('bool') is third in form fields")
        self.assertEqual('longtext', field_names[3],
            "fourth field in xmlobject ('longtext') is fourth in form fields")

        class MyTestObject(xmlmap.XmlObject):
            ROOT_NAME = 'foo'
            a = xmlmap.StringField('a')
            z = xmlmap.StringField('z')
            b = xmlmap.StringField('b')
            y = xmlmap.StringField('y')

        myform = xmlobjectform_factory(MyTestObject)
        form = myform()
        field_names = form.base_fields.keys()
        self.assertEqual('a', field_names[0],
            "first field in xmlobject ('a') is first in form fields")
        self.assertEqual('z', field_names[1],
            "second field in xmlobject ('z') is second in form fields")
        self.assertEqual('b', field_names[2],
            "third field in xmlobject ('b') is third in form fields")
        self.assertEqual('y', field_names[3],
            "fourth field in xmlobject ('y') is fourth in form fields")

        # what happens to order on an xmlobject with inheritance?

    def test_update_instance(self):
        # initialize data the same way a view processing a POST would
        update_form = TestForm(self.post_data, instance=self.testobj)
        # check that form is valid - if no errors, this populates cleaned_data
        self.assertTrue(update_form.is_valid())

        instance = update_form.update_instance()
        self.assert_(isinstance(instance, TestObject))
        self.assertEqual(21, instance.int)
        self.assertEqual(False, instance.bool)
        self.assertEqual('b', instance.id)
        self.assertEqual('completely new text content', instance.longtext)
        
        # spot check that values were set properly in the xml
        xml = instance.serialize()
        self.assert_('id="b"' in xml)
        self.assert_('<boolean>no</boolean>' in xml)

        # test save on form with no pre-existing xmlobject instance
        class SimpleForm(XmlObjectForm):
            class Meta:
                model = TestObject
                fields = ['id', 'bool', 'longtext'] # fields with simple, top-level xpaths
                # creation for nested node not yet supported in xmlmap - excluding int
                exclude = ['children']      # exclude subform to simplify testing

        new_form = SimpleForm({'id': 'A1', 'bool': True, 'longtext': 'la-di-dah'})
        self.assertTrue(new_form.is_valid())
        instance = new_form.update_instance()
        self.assert_(isinstance(instance, TestObject),
            "update_instance on unbound xmlobjectform returns correct xmlobject instance")
        self.assertEqual(True, instance.bool)
        self.assertEqual('A1', instance.id)
        self.assertEqual('la-di-dah', instance.longtext)
        # spot check values in created-from-scratch xml
        xml = instance.serialize()
        self.assert_('id="A1"' in xml)
        self.assert_('<boolean>yes</boolean>' in xml)


    def test_unsupported_fields(self):
        # xmlmap fields that XmlObjectForm doesn't know how to convert into form fields
        # should raise an exception

        class DateObject(xmlmap.XmlObject):
            ROOT_NAME = 'foo'
            date = DateField('date')

        self.assertRaises(Exception, xmlobjectform_factory, DateObject)

        class ListObject(xmlmap.XmlObject):
            ROOT_NAME = 'foo'
            list = xmlmap.StringListField('bar')

        self.assertRaises(Exception, xmlobjectform_factory, ListObject)

    def test_subforms(self):
        # nodefields should be created as subforms on the object
        subform = self.new_form.subforms['children']
        self.assert_(isinstance(subform, XmlObjectForm),
            'form has an XmlObjectForm subform')

        expected, got = 'TestSubobjectXmlObjectForm', subform.__class__.__name__
        self.assertEqual(expected, got,
            "autogenerated subform class name: expected %s, got %s" % \
                (expected, got))
        self.assertEqual(TestSubobject, subform.Meta.model,
            "xmlobject class 'TestSubobject' correctly set as model in subform class Meta")
        expected, got = 'children', subform.prefix
        self.assertEqual(expected, got,
            "subform prefix is set to the name of the corresponding nodefield; expected %s, got %s" \
                % (expected, got))
        # subform fields - uses same logic tested above, so doesn't need thorough testing here
        self.assert_('val' in subform.base_fields, 'val field is present in subform fields')
        self.assert_('id2' in subform.base_fields, 'int field is present in subform fields')

        # subform is initialized with appropriate instance data
        subform = self.update_form.subforms['children']
        # initial values from subobject portion of test fixture
        expected, got = 'forty-two', subform.initial['id2']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'id2' should be %s, got %s" % \
            (expected, got))
        expected, got = 42, subform.initial['val']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'val' should be %s, got %s" % \
            (expected, got))

        # initialize with request data to test subform validation / instance update
        update_form = TestForm(self.post_data, instance=self.testobj)
        subform = update_form.subforms['children']
        self.assertTrue(update_form.is_valid()) 
        # nodefield instance should be set by main form update
        instance = update_form.update_instance()        
        self.assertEqual(2, instance.children.val)
        self.assertEqual('two', instance.children.id2)

    def test_is_valid(self):
        # missing required fields for main form but not subform
        form = TestForm({'int': 21, 'children-id2': 'two', 'children-val': 2 })
        self.assertFalse(form.is_valid(),
            "form is not valid when required top-level fields are missing")
        # no subform fields
        form = TestForm({'int': 21, 'bool': True, 'id': 'b', 'longtext': 'short'})
        self.assertFalse(form.is_valid(),
            "form is not valid when required subform fields are missing")

        form = TestForm(self.post_data)
        self.assertTrue(form.is_valid(),
            "form is valid when top-level and subform required fields are present")

