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
from recaptcha.client import captcha
import unittest

from django import forms
from django.conf import settings
from django.forms import ValidationError
from django.forms.formsets import BaseFormSet

from eulcore import xmlmap
from eulcore.xmlmap.fields import DateField     # not yet supported - testing for errors
from eulcore.django.forms import XmlObjectForm, xmlobjectform_factory, SubformField
from eulcore.django.forms.xmlobject import XmlObjectFormType
from eulcore.django.forms.fields import W3CDateWidget, DynamicSelect, DynamicChoiceField
from eulcore.django.forms import captchafield


# test xmlobject and xml content to generate test form

class TestSubobject(xmlmap.XmlObject):
    ROOT_NAME = 'bar'
    val = xmlmap.IntegerField('baz', required=False)
    id2 = xmlmap.StringField('@id')

class OtherTestSubobject(TestSubobject):
    ROOT_NAME = 'plugh'

class TestObject(xmlmap.XmlObject):
    ROOT_NAME = 'foo'
    id = xmlmap.StringField('@id', verbose_name='My Id', help_text='enter an id')
    int = xmlmap.IntegerField('bar[2]/baz')
    bool = xmlmap.SimpleBooleanField('boolean', 'yes', 'no')
    longtext = xmlmap.StringField('longtext', normalize=True, required=False)
    child = xmlmap.NodeField('bar[1]', TestSubobject, verbose_name='Child bar1')
    children = xmlmap.NodeListField('bar', TestSubobject)
    other_child = xmlmap.NodeField('plugh', OtherTestSubobject)
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
        'other_child-val': '0',
        'other_child-id2': 'xyzzy',
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
        expected, got = 'My Id', formfields['id'].label
        self.assertEqual(expected, got, "form field label should be set to " + \
            "from xmlmap field verbose name; expected %s, got %s" % (expected, got))
        expected, got = 'enter an id', formfields['id'].help_text
        self.assertEqual(expected, got, "form field help text should be set to " + \
            "from xmlmap field help text; expected %s, got %s" % (expected, got))

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

    def test_unchanged_initial_param(self):
        # initial data dictionary passed in should not be changed by class init
        my_initial_data = {'foo': 'bar'}
        initial_copy = my_initial_data.copy()
        TestForm(instance=self.testobj, initial=initial_copy)
        self.assertEqual(my_initial_data, initial_copy)

    def test_field_value_from_instance(self):
        # when form is initialized from an xmlobject instance, form should 
        # have initial field values be pulled from the xml object
        
        initial_data = self.update_form.initial   # initial values set on BaseForm
        expected, got = 'a', initial_data['id']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'id' should be %s, got %s" % \
            (expected, got))

        expected, got = 13, initial_data['int']
        self.assertEqual(expected, got,
           "initial instance-based form value for 'int' should be %s, got %s" % \
            (expected, got))

        expected, got = True, initial_data['bool']
        self.assertEqual(expected, got,
           "initial instance-based form value for 'bool' should be %s, got %s" % \
            (expected, got))

        # test with prefixes
        update_form = TestForm(instance=self.testobj, prefix='pre')
        initial_data = update_form.initial   # initial values set on BaseForm
        expected, got = 'a', initial_data['id']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'pre-id' should be %s, got %s" % \
            (expected, got))
        # the *rendered* field should actually have the value
        # ... there should probably be a way to inspect the BoundField value directly (can't get it to work)
        self.assert_('value="%s"' % expected in str(update_form['id']),
            'rendered form field has correct initial value')
        self.assert_('name="pre-id"' in str(update_form['id']),
            'rendered form field has a name with the requested prefix')
        self.assert_('id="id_pre-id"' in str(update_form['id']),
            'rendered form field has an id with the requested prefix')

        expected, got = 13, initial_data['int']
        self.assertEqual(expected, got,
           "initial instance-based form value for 'int' should be %s, got %s" % \
            (expected, got))

        expected, got = True, initial_data['bool']
        self.assertEqual(expected, got,
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
        self.assertEqual(0, instance.other_child.val)
        
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

        # formset deletion
        data = self.post_data.copy()
        # update post data to test deleting items
        data.update({
            'children-INITIAL_FORMS': 4,        # only initial forms can be deleted
            'children-0-DELETE': True,
            'children-2-DELETE': True,
        })
        # make a copy object, since the instance will be updated by the form
        testobj = xmlmap.load_xmlobject_from_string(self.testobj.serialize(), TestObject)
        update_form = TestForm(data, instance=self.testobj)
        # check that form is valid - if no errors, this populates cleaned_data
        self.assertTrue(update_form.is_valid())
        instance = update_form.update_instance()
        # children 0 and 2 should be removed from the updated instance
        self.assert_(testobj.children[0] not in instance.children)
        self.assert_(testobj.children[2] not in instance.children)

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
        # check rendered field for initial value
        self.assert_('value="%s"' % expected in str(subform['id2']),
            'rendered subform field has correct initial value')
        expected, got = 42, subform.initial['val']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'val' should be %s, got %s" % \
            (expected, got))
        self.assert_('value="%s"' % expected in str(subform['val']),
            'rendered subform field has correct initial value')

        # subform label
        expected_val = 'Child bar1'
        self.assertEqual(expected_val, subform.form_label,
            'subform form_label should be set from xmlobject field verbose_name; ' +
            'expected %s, got %s' % (expected_val, subform.form_label))

        # test with prefixes
        update_form = TestForm(instance=self.testobj, prefix='pre')
        subform = update_form.subforms['child']
        expected, got = 'forty-two', subform.initial['id2']
        self.assertEqual(expected, got,
            "initial instance-based subform value for 'id2' should be %s, got %s" % \
            (expected, got))
        self.assert_('value="%s"' % expected in str(subform['id2']),
            'rendered subform field has correct initial value')
        expected, got = 42, subform.initial['val']
        self.assertEqual(expected, got,
            "initial instance-based form value for 'val' should be %s, got %s" % \
            (expected, got))
        self.assert_('value="%s"' % expected in str(subform['val']),
            'rendered subform field has correct initial value')

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

        # formset label
        self.assertEqual('Children', formset.form_label,
            'formset form_label should be set based on xmlobject field name; ' +
            'excpected Children, got %s' % formset.form_label)


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
         # check rendered fields for initial values
        self.assert_('value="forty-two"' in str(formset.forms[0]['id2']),
            'rendered formset field has correct initial value')
        self.assert_('value="42"' in str(formset.forms[0]['val']),
            'rendered formset field has correct initial value')
        self.assert_('value=""' not in str(formset.forms[1]['id2']),
            'rendered formset field has correct initial value')
        self.assert_('value="13"' in str(formset.forms[1]['val']),
            'rendered formset field has correct initial value')

        # initialize with prefix
        update_form = TestForm(instance=self.testobj, prefix='pre')
        formset = update_form.formsets['children']
        self.assertEqual('forty-two', formset.forms[0].initial['id2'])
        self.assertEqual(42, formset.forms[0].initial['val'])
        self.assertEqual(None, formset.forms[1].initial['id2'])
        self.assertEqual(13, formset.forms[1].initial['val'])
        self.assert_('value="forty-two"' in str(formset.forms[0]['id2']),
            'rendered formset field has correct initial value')
        self.assert_('value="42"' in str(formset.forms[0]['val']),
            'rendered formset field has correct initial value')
        self.assert_('value=""' not in str(formset.forms[1]['id2']),
            'rendered formset field has correct initial value')
        self.assert_('value="13"' in str(formset.forms[1]['val']),
            'rendered formset field has correct initial value')

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

        subform_label = 'TEST ME'

        class MyForm(TestForm):
            child = SubformField(formclass=MySubForm, label=subform_label)
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
        
        # subform label - subformfield label should supercede field-based label
        self.assertEqual(subform_label, form.subforms['child'].form_label,
            'subform generated by SubformField form_label should be set by subform label; ' + \
            'expected %s, got %s' % (subform_label, form.subforms['child'].form_label))


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

        # invalid initial value results in default MM DD YYYY placeholder values.
        inputs = self.widget.render('date', 'foo-bar-baz')
        self.assert_('value="MM"' in inputs,
            'Invalid intial value should result in a default MM in the month input')
        self.assert_('value="DD"' in inputs,
            'Invalid intial value should result in a default DD in the day input')
        self.assert_('value="YYYY"' in inputs,
            'Invalid intial value should result in a default YYYY in the year input')


class DynamicSelectTest(unittest.TestCase):
    def setUp(self):
        self.widget = DynamicSelect(choices=self.get_choices)
        self.choices = []

    def get_choices(self):
        return self.choices

    def test_render(self):
        self.choices = [('1', 'one'),
                        ('2', 'two'),
                        ('3', 'three')]
        html = self.widget.render('values', None)
        self.assert_('one' in html, 'render includes "one"')
        self.assert_('two' in html, 'render includes "two"')
        self.assert_('three' in html, 'render includes "three"')

        self.choices = [('a', 'alpha'),
                        ('b', 'beta'),
                        ('c', 'gamma')]
        html = self.widget.render('values', None)
        self.assert_('alpha' in html, 'render includes "alpha"')
        self.assert_('beta' in html, 'render includes "beta"')
        self.assert_('gamma' in html, 'render includes "gamma"')

class DynamicChoiceFieldTest(unittest.TestCase):
    def setUp(self):
        self.field = DynamicChoiceField(choices=self.get_choices)
        self.choices = []

    def get_choices(self):
        return self.choices

    def test_choices(self):
        self.choices = [('1', 'one'),
                        ('2', 'two'),
                        ('3', 'three')]
        self.assertEqual(self.choices, self.field.choices)

    def test_set_choices(self):
        def other_choices():
            return [('a', 'ay'), ('b', 'bee'), ('c', 'cee')]

        # should be able to set choices with a new callable
        self.field.choices = other_choices
        self.assertEqual(other_choices(), self.field.choices)
        # updating field choices also updates widget choices
        self.assertEqual(other_choices(), self.field.widget.choices)
          




class MockCaptcha:
    'Mock captcha client to allow testing without querying captcha servers'
    response = captcha.RecaptchaResponse(True)
    submit_args = {}
    display_arg = None

    def displayhtml(self, pubkey):
        self.display_arg = pubkey
        return ''

    def submit(self, challenge, response, private_key, remote_ip):
        self.submit_args = {'challenge': challenge, 'response': response,
            'private_key': private_key, 'remote_ip': remote_ip}
        return self.response

class MockCaptchaTest(unittest.TestCase):

    captcha_module = captchafield

    def setUp(self):
        # swap out captcha with mock
        self._captcha = self.captcha_module.captcha
        self.captcha_module.captcha = MockCaptcha()
        # set required captcha configs
        self._captcha_private_key = getattr(settings, 'RECAPTCHA_PRIVATE_KEY', None)
        self._captcha_public_key = getattr(settings, 'RECAPTCHA_PUBLIC_KEY', None)
        self._captcha_opts = getattr(settings, 'RECAPTCHA_OPTIONS', None)
        settings.RECAPTCHA_PRIVATE_KEY = 'mine & mine alone'
        settings.RECAPTCHA_PUBLIC_KEY = 'anyone can see this'
        settings.RECAPTCHA_OPTIONS = {}

    def tearDown(self):
        # restore real captcha
        self.captcha_module.captcha = self._captcha
        # restore captcha settings
        if self._captcha_private_key is None:
            delattr(settings, 'RECAPTCHA_PRIVATE_KEY')
        else:
            settings.RECAPTCHA_PRIVATE_KEY = self._captcha_private_key
        if self._captcha_public_key is None:
            delattr(settings, 'RECAPTCHA_PUBLIC_KEY')
        else:
            settings.RECAPTCHA_PUBLIC_KEY = self._captcha_public_key
        if self._captcha_opts is None:
            delattr(settings, 'RECAPTCHA_OPTIONS')
        else:
            settings.RECAPTCHA_OPTIONS = self._captcha_opts


class ReCaptchaWidgetTest(MockCaptchaTest):

    def test_render(self):
        widget = captchafield.ReCaptchaWidget()
        html = widget.render('captcha', None)
        self.assertTrue(html)
        self.assertEqual(settings.RECAPTCHA_PUBLIC_KEY, self.captcha_module.captcha.display_arg,
            'captcha challenge should be generated with public key from settings')
        self.assert_('<script' not in html,
            'widget output should not include <script> tag when no render options are set')

        widget = captchafield.ReCaptchaWidget(attrs={'theme': 'white'})
        html = widget.render('captcha', None)
        self.assert_('<script' in html,
            'widget output should include <script> tag when no render options are set')
        self.assert_('var RecaptchaOptions = {"theme": "white"};' in html,
            'recaptcha options should be generated from widget attributes')

        settings.RECAPTCHA_OPTIONS = {'lang': 'fr'}
        widget = captchafield.ReCaptchaWidget()
        html = widget.render('captcha', None)
        self.assert_('var RecaptchaOptions = {"lang": "fr"};' in html,
            'recaptcha options should be generated from RECAPTCHA_OPTIONS in settings')

        widget = captchafield.ReCaptchaWidget(attrs={'lang': 'en'})
        html = widget.render('captcha', None)
        self.assert_('var RecaptchaOptions = {"lang": "en"};' in html,
            'widget attributes should supercede recaptcha options from RECAPTCHA_OPTIONS in settings')

class ReCaptchaFieldTest(MockCaptchaTest):

    def test_clean(self):
        field = captchafield.ReCaptchaField()

        data = {'challenge': 'knock knock', 'response': 'who\'s there?',
            'remote_ip': '127.0.0.1'}
        field.clean(data)
        # check that captcha was submitted correctly
        self.assertEqual(data['challenge'],
            captchafield.captcha.submit_args['challenge'])
        self.assertEqual(data['response'],
            captchafield.captcha.submit_args['response'])
        self.assertEqual(settings.RECAPTCHA_PRIVATE_KEY,
            captchafield.captcha.submit_args['private_key'])
        self.assertEqual(data['remote_ip'], self.captcha_module.captcha.submit_args['remote_ip'])

        # simulate invalid captcha response
        self.captcha_module.captcha.response.is_valid = False
        self.captcha_module.captcha.response.err_code = 'incorrect-captcha-sol'
        self.assertRaises(ValidationError, field.clean, data)

        # other error
        self.captcha_module.captcha.response.err_code = 'invalid-referrer'
        self.assertRaises(ValidationError, field.clean, data)

        # restore success response
        self.captcha_module.captcha.response.is_valid = True
        self.captcha_module.captcha.response.err_code = None
