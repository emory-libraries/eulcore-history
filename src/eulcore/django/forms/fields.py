# file django/forms/fields.py
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

from django.core.validators import RegexValidator
from django.forms import CharField
from django.forms.widgets import Widget, TextInput
from django.utils.safestring import mark_safe

# regular expression to validate and parse W3C dates
W3C_DATE_RE = re.compile(r'^(?P<year>\d{4})(?:-(?P<month>[0-1]\d)(?:-(?P<day>[0-3]\d))?)?$')
validate_w3c_date = RegexValidator(W3C_DATE_RE,
    u'Enter a valid W3CDFT date in one of these formats: YYYY, YYYY-MM, or YYYY-MM-DD',
    'invalid')

class W3CDateWidget(Widget):
    '''Multi-part date widget that generates three text input boxes for year,
    month, and day.  Expects and generates dates in any of these W3C formats,
    depending on which fields are filled in: YYYY-MM-DD, YYYY-MM, or YYYY.   
    '''

    # based in part on SelectDateWidget from django.forms.extras.widgets
    month_field = '%s_month'
    day_field = '%s_day'
    year_field = '%s_year'

    def value_from_datadict(self, data, files, name):
        '''Generate a single value from multi-part form data.  Constructs a W3C
        date based on values that are set, leaving out day and month if they are
        not present.
        
        :param data: dictionary of data submitted by the form 
        :param files: - unused
        :param name: base name of the form field
        :returns: string value 
        '''

        y = data.get(self.year_field % name)
        m = data.get(self.month_field % name)
        d = data.get(self.day_field % name)
        date = y
        if m:
            date += '-%s' % m
            if d:
                date += '-%s' % d
        return date

    def render(self, name, value, attrs=None):
        '''Render the widget as HTML inputs for display on a form.

        :param name: form field base name
        :param value: date value
        :param attrs: - unused
        :returns: HTML text with three inputs for year/month/day
        '''

        # expects a value in format YYYY-MM-DD or YYYY-MM or YYYY (or empty/None)
        year, month, day = '', '', ''
        if value:
            # use the regular expression to pull out year, month, and day values
            # if regular expression does not match, inputs will be empty
            match = W3C_DATE_RE.match(value)
            if match:
                date_parts = match.groupdict()
                year = date_parts['year']
                month = date_parts['month']
                day = date_parts['day']
        year_html = self.create_textinput(name, self.year_field, year, size=4, title='4-digit year')
        month_html = self.create_textinput(name, self.month_field, month, size=2, title='2-digit month')
        day_html = self.create_textinput(name, self.day_field, day, size=2, title='2-digit day')

        output = [year_html, month_html, day_html]
        return mark_safe(u' / \n'.join(output))

    def create_textinput(self, name, field, value, **extra_attrs):
        '''Generate and render a :class:`django.forms.widgets.TextInput` for
        a single year, month, or day input.

        If size is specified in the extra attributes, it will also be used to
        set the maximum length of the field.

        :param name: base name of the input field
        :param field: pattern for this field (used with name to generate input name)
        :param value: initial value for the field
        :param extra_attrs: any extra widget attributes
        :returns: rendered HTML output for the text input
        '''
        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = 'id_%s' % name

        # use size to set maximum length
        if 'size' in extra_attrs:
            extra_attrs['maxlength'] = extra_attrs['size']
        local_attrs = self.build_attrs(id=field % id_, **extra_attrs)
        input = TextInput()
        return input.render(field % name, value, local_attrs)


class W3CDateField(CharField):
    '''W3C date field that uses a :class:`W3CDateWidget` for presentation
    and uses a simple regular expression to do basic validation on the input
    (but does not actually test that it is a valid date).
    '''
    widget = W3CDateWidget
    default_error_messages = {
        'invalid':  u'Enter a date in one of these formats: YYYY, YYYY-MM, or YYYY-MM-DD',
    }
    default_validators = [validate_w3c_date]
