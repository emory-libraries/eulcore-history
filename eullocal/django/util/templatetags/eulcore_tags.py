# file django/util/templatetags/eulcore_tags.py
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

# Various template tags and such.

'''
"The poet produces something beautiful by fixing his attention on something
real."
- Simone Weil
'''
# This contains cutom template tags and filters for the project app.

import re

from django import template

register = template.Library()

# CUSTOM TAGS

# This method is a modification of Vincent Foley's code snippet located at
# http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/
# The modification is in using a 'url as' statement in the template to keep
# from hard coding URLs into the template.
@register.simple_tag
def activepage(request, ptrn):
    '''
    If the current request path matches the pattern returns the word active.

    '''
    if request.path.endswith(ptrn):
        return 'active'
    return ''

@register.simple_tag
def activebase(request, ptrn):
    '''
    Returns active if the start of the current request path matches ptrn.

    '''
    if re.search(ptrn, request.path):
        return 'active'
    return ''

# CUSTOM FILTERS

# CUSTOM BLOCKS