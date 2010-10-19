# file django/forms/tests.py
# 
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import re
import unittest

from django import forms
from django.forms.formsets import BaseFormSet

from eulcore import xmlmap
from eulcore.xmlmap.fields import DateField     # not yet supported - testing for errors
from eulcore.django.forms import XmlObjectForm, xmlobjectform_factory, SubformField
from eulcore.django.forms.xmlobject import XmlObjectFormType
from eulcore.django.forms.fields import W3CDateWidget


# test xmlobject and xml content to generate test form

class TestSubobject(xmlmap.XmlObject):
    ROOT_NAME = 'bar'
    val = xmlmap.IntegerField('baz', required=False)
    id2 = xmlmap.StringField('@id')

class TestObject(xmlmap.XmlObject):
    ROOT_NAME = 'foo'
    id = xmlmap.StringField('@id')
    int = xmlmap.IntegerField('bar[2]/baz')
    bool = xmlmap.SimpleBooleanField('boolean', 'yes', 'no')
    longtext = xmlmap.StringField('longtext', normalize=True, required=False)
    child = xmlmap.NodeField('bar[1]', TestSubobject)
    children = xmlmap.NodeListField('bar', TestSubobject)
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
        'child-id2': 'two',
        'child-val': 2,
        # include base form data so form will be valid
        'longtext': 'completely new text content',
        'int': 21,
        'bool': False,
        'id': 'b',
        'my_opt': 'c',
        # children formset
        'children-TOTAL_FORMS': 5,
        'children-INITIAL_FORMS': 2,
        'children-0-id2': 'two',
        'children-0-val': 2,
        'children-1-id2': 'twenty-one',
        'children-1-val': 21,
        'children-2-id2': 'five',
        'children-2-val': 5,
        'children-3-id2': 'four',
        'children-3-val': 20,
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

        # required value from xmlobject field
        self.assertFalse(formfields['longtext'].required,
            'form field generated from xmlobject field with required=False is not required')

    def test_field_value_from_instance(self):
        # when form is initialized from an xmlobject instance, form should 
        # have initial field values be pulled from the xml object
        
        initial_data = self.update_form.initial   # initial values set on BaseForm
        expected, got = 'a', initial_data['id']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'id' should be %s, got %s" % \
            (expected, got))

        expected, got = 13, initial_data['int']
        self.assertEqual(expected, initial_data['int'],
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
        myfields = ['int', 'bool', 'child.val']
        myform = xmlobjectform_factory(TestObject, fields=myfields)
        form = myform()
        self.assert_('int' in form.base_fields,
            'int field is present in form fields when specified in field list')
        self.assert_('bool' in form.base_fields,
            'bool field is present in form fields when specified in field list')
        self.assert_('id' not in form.base_fields,
            'id field is not present in form fields when not specified in field list')

        self.assert_('child' in form.subforms,
            'child field is present in subforms when specified in nested field list')
        self.assert_('val' in form.subforms['child'].base_fields,
            'val field present in child subform fields when specified in nested field list')
        self.assert_('id2' not in form.subforms['child'].base_fields,
            'id2 field is not present in child subform fields when not specified in nested field list')

        # form field order should match order in fields list
        self.assertEqual(form.base_fields.keys(), ['int', 'bool'])

        # second variant to confirm field order
        myfields = ['longtext', 'int', 'bool']
        myform = xmlobjectform_factory(TestObject, fields=myfields)
        form = myform()
        self.assertEqual(myfields, form.base_fields.keys())

    def test_exclude(self):
        # if exclude is specified, those fields should not be listed
        myform = xmlobjectform_factory(TestObject,
            exclude=['id', 'bool', 'child.id2'])
        form = myform()
        self.assert_('int' in form.base_fields,
            'int field is present in form fields when not excluded')
        self.assert_('longtext' in form.base_fields,
            'longtext field is present in form fields when not excluded')
        self.assert_('bool' not in form.base_fields,
            'bool field is not present in form fields when excluded')
        self.assert_('id' not in form.base_fields,
            'id field is not present in form fields when excluded')
        self.assert_('child' in form.subforms,
            'child subform is present in form fields when subfields excluded')
        self.assert_('val' in form.subforms['child'].base_fields,
            'val field is present in child subform fields when not excluded')
        self.assert_('id2' not in form.subforms['child'].base_fields,
            'id2 field is not present in child subform fields when excluded')

        # another variant for excluding an entire subform
        myform = xmlobjectform_factory(TestObject,
            exclude=['child'])
        form = myform()
        self.assert_('child' not in form.subforms,
            'child subform is not present in form fields when excluded')

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
        # id, int, bool, longtext, [child]
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
                exclude = ['child']      # exclude subform to simplify testing

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
        subform = self.new_form.subforms['child']
        self.assert_(isinstance(subform, XmlObjectForm),
            'form has an XmlObjectForm subform')

        expected, got = 'TestSubobjectXmlObjectForm', subform.__class__.__name__
        self.assertEqual(expected, got,
            "autogenerated subform class name: expected %s, got %s" % \
                (expected, got))
        self.assertEqual(TestSubobject, subform.Meta.model,
            "xmlobject class 'TestSubobject' correctly set as model in subform class Meta")
        expected, got = 'child', subform.prefix
        self.assertEqual(expected, got,
            "subform prefix is set to the name of the corresponding nodefield; expected %s, got %s" \
                % (expected, got))
        # subform fields - uses same logic tested above, so doesn't need thorough testing here
        self.assert_('val' in subform.base_fields, 'val field is present in subform fields')
        self.assert_('id2' in subform.base_fields, 'int field is present in subform fields')

        # required setting from xmlobject field
        self.assertFalse(subform.base_fields['val'].required,
            'form field generated from xmlobject field with required=False is not required')

        # subform is initialized with appropriate instance data
        subform = self.update_form.subforms['child']
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
        subform = update_form.subforms['child']
        self.assertTrue(update_form.is_valid()) 
        # nodefield instance should be set by main form update
        instance = update_form.update_instance()        
        self.assertEqual(2, instance.child.val)
        self.assertEqual('two', instance.child.id2)

    def test_formsets(self):
        # nodelistfields should be created as formsets on the object
        formset = self.new_form.formsets['children']
        self.assert_(isinstance(formset, BaseFormSet),
            'form has a BaseFormSet formset')
        self.assertEqual('TestSubobjectXmlObjectFormFormSet', formset.__class__.__name__)

        subform = formset.forms[0]
        self.assert_(isinstance(subform, XmlObjectForm),
            'formset forms are XmlObjectForms')
        self.assertEqual('TestSubobjectXmlObjectForm', subform.__class__.__name__)
        self.assertEqual('children-0', subform.prefix)

        # subform fields
        self.assert_('val' in subform.base_fields,
            'val field is present in subform fields')
        self.assert_('id2' in subform.base_fields,
            'id2 field is present in subform fields')

        # initialize with an instance and verify initial values
        formset = self.update_form.formsets['children']
        self.assertEqual('forty-two', formset.forms[0].initial['id2'])
        self.assertEqual(42, formset.forms[0].initial['val'])
        self.assertEqual(None, formset.forms[1].initial['id2'])
        self.assertEqual(13, formset.forms[1].initial['val'])

        # initialize with an instance and form data
        update_form = TestForm(self.post_data, instance=self.testobj)
        formset = update_form.formsets['children']
        self.assertTrue(update_form.is_valid())
        self.assertTrue(formset.is_valid())
        instance = update_form.update_instance()
        self.assertEqual(4, len(instance.children))
        self.assertEqual('two', instance.children[0].id2)
        self.assertEqual(2, instance.children[0].val)
        self.assertEqual('twenty-one', instance.children[1].id2)
        self.assertEqual(21, instance.children[1].val)
        self.assertEqual('five', instance.children[2].id2)
        self.assertEqual(5, instance.children[2].val)
        self.assertEqual('four', instance.children[3].id2)
        self.assertEqual(20, instance.children[3].val)


    def test_is_valid(self):
        # missing required fields for main form but not subform or formsets
        form = TestForm({'int': 21, 'child-id2': 'two', 'child-val': 2,
                         'children-TOTAL_FORMS': 5, 'children-INITIAL_FORMS': 2, })
        self.assertFalse(form.is_valid(),
            "form is not valid when required top-level fields are missing")

        # no subform fields but have formsets
        form = TestForm({'int': 21, 'bool': True, 'id': 'b', 'longtext': 'short',
                         'children-TOTAL_FORMS': 5, 'children-INITIAL_FORMS': 2, })
        self.assertFalse(form.is_valid(),
            "form is not valid when required subform fields are missing")

        form = TestForm(self.post_data, instance=self.testobj)
        # NOTE: passing in object instance because validation now attempts to initialize,
        # and dynamic creation of nodes like bar[2]/baz is currently not supported
        self.assertTrue(form.is_valid(),
            "form is valid when top-level and subform required fields are present")


    def test_not_required(self):
        class MyForm(TestForm):
            id = forms.CharField(label='my id', required=False)

        data = self.post_data.copy()
        data['id'] = ''
        form = MyForm(data)
        self.assertTrue(form.is_valid(),
            'form is valid when non-required override field is empty')
        instance = form.update_instance()
        # empty string should actually remove node frome the xml
        self.assertEqual(None, instance.id)
        self.assertEqual(0, instance.node.xpath('count(@id)'))

    def test_override_subform(self):
        class MySubForm(XmlObjectForm):
            id2 = forms.URLField(label="my id")
            class Meta:
                model = TestSubobject

        class MyForm(TestForm):
            child = SubformField(formclass=MySubForm, label="TEST ME")
            class Meta:
                model = TestObject
                fields = ['id', 'int', 'child']

        form = MyForm()
        self.assert_(isinstance(form.subforms['child'], MySubForm),
            "child subform should be instance of MySubForm, got %s instead" % \
            form.subforms['child'].__class__)
        self.assertEqual('my id', form.subforms['child'].fields['id2'].label)        
        self.assert_('TEST ME' not in str(form),
                "subform pseudo-field should not appear in form output")

    def test_override_formset(self):
        class MySubForm(XmlObjectForm):
            id2 = forms.URLField(label="my id")
            class Meta:
                model = TestSubobject

        class MyForm(TestForm):
            children = SubformField(formclass=MySubForm, label="TEST ME")

        form = MyForm()
        self.assert_(isinstance(form.formsets['children'].forms[0], MySubForm),
            "children formset form should be instance of MySubForm, got %s instead" % \
            form.formsets['children'].forms[0].__class__)
        self.assertEqual('my id', form.formsets['children'].forms[0].fields['id2'].label)
        self.assert_('TEST ME' not in str(form),
                "subform pseudo-field should not appear in form output")

    def test_override_subform_formset(self):
        # test nested override - a subform with a formset
        class MyTestSubObj(TestSubobject):
            parts = xmlmap.NodeListField('parts', TestSubobject)
            
        class MySubFormset(XmlObjectForm):
            uri = forms.URLField(label='uri')
            class Meta:
                model = MyTestSubObj

        class MySubForm(XmlObjectForm):
            parts = SubformField(formclass=MySubFormset)
            class Meta:
                model = MyTestSubObj
            
        class MyTestObj(TestObject):
            child = xmlmap.NodeField('bar[1]', MyTestSubObj)

        class MyForm(TestForm):
            child = SubformField(formclass=MySubForm, label="TEST ME")
            class Meta:
                model = MyTestObj

        form = MyForm()
        subformset = form.subforms['child'].formsets['parts'].forms[0]
        self.assert_(isinstance(subformset, MySubFormset))


class W3CDateWidgetTest(unittest.TestCase):

    def setUp(self):
        self.widget = W3CDateWidget()

    def test_value_from_datadict(self):
        name = 'date'
        data = {'date_year': '1999',
            'date_month': '01',
            'date_day': '31'
        }
        self.assertEqual('1999-01-31', self.widget.value_from_datadict(data, [], name))
        data['date_day'] = ''
        self.assertEqual('1999-01', self.widget.value_from_datadict(data, [], name))
        data['date_month'] = ''
        self.assertEqual('1999', self.widget.value_from_datadict(data, [], name))

        # if day is specified but no month,  day will be ignored
        data['date_day'] = '15'
        self.assertEqual('1999', self.widget.value_from_datadict(data, [], name))

        self.assertEqual(None, self.widget.value_from_datadict({}, [], name),
            'value_from_datadict returns None when expected inputs are not present')

    def test_create_textinput(self):
        input = self.widget.create_textinput('date', '%s_month', '22', title='foo')
        self.assert_(input.startswith('<input'))
        self.assert_('type="text"' in input)
        self.assert_('name="date_month"' in input)
        self.assert_('id="id_date_month"' in input)
        self.assert_('value="22"' in input)
        self.assert_('title="foo"' in input)

    def test_render(self):
        inputs = self.widget.render('date', '1999-12-31')
        re_flags = re.MULTILINE | re.DOTALL
        self.assert_(re.match(r'<input.*>.*\/.*<input.*>.*\/.*<input.*>', inputs,
            re_flags), 'render output has 3 inputs separated by /')

        self.assert_(re.match(r'<input.*name="date_year".*maxlength="4"', inputs, re_flags),
            'year input is in rendered widget output with max length of 4')
        self.assert_(re.match(r'<input.*name="date_month".*maxlength="2"', inputs, re_flags),
            'month input is in rendered widget output with max length of 2')
        self.assert_(re.match(r'<input.*name="date_day".*maxlength="2"', inputs, re_flags),
            'day input is in rendered widget output with max length of 2')

        # invalid initial value results in empty inputs
        inputs = self.widget.render('date', 'foo-bar-baz')
        self.assert_('value="' not in inputs,
            'invalid intial value results in no pre-set value on any of the date inputs')
