"""Customized decorators that enhance the default behavior of
:meth:`django.contrib.auth.decorators.permission_required`.

The default behavior of :meth:`django.contrib.auth.decorators.permission_required`
for any user does not meet the required permission level is to redirect them to
the login page-- even if that user is already logged in. For more discussion of 
this behavior and current status in Django, see:
http://code.djangoproject.com/ticket/4617

These decorators work the same way as the Django equivalents, with the added
feature that if the user is already logged in and does not have the required
permission, they will see 403 page instead of the login page.

The decorators should be used exactly the same as their django equivalents.

The code is based on the django snippet code at http://djangosnippets.org/snippets/254/
"""

from eulcore.django.auth.decorators import *