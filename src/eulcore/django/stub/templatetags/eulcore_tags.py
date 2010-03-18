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