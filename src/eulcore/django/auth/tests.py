# file django/auth/tests.py
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

from os import path

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.http import HttpResponse, HttpRequest
from django.test import TestCase

from eulcore.django.auth import user_passes_test_with_403, permission_required_with_403

def simple_view(request):
    "a simple view for testing custom auth decorators"
    return HttpResponse("Hello, World")

class PermissionRequired403_Test(TestCase):
    fixtures =  ['users']

    def setUp(self):
        self.request = HttpRequest()
        self.request.user = AnonymousUser()

        self.staff_user = User.objects.get(username='staff')
        self.super_user = User.objects.get(username='super')
        
        self._template_dirs = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            path.join(path.dirname(path.abspath(__file__)), 'fixtures'), 
        )

        # decorate simple view above for testing
        self.login_url = '/my/login/page'
        decorator = permission_required_with_403('is_superuser', self.login_url)
        self.decorated = decorator(simple_view)

    def tearDown(self):
        # restore any configured template dirs
        settings.TEMPLATE_DIRS = self._template_dirs

    def test_anonymous(self):        
        response = self.decorated(self.request)
        self.assert_(response['Location'].startswith(self.login_url),
                "decorated view redirects to login page for non-logged in user")
        expected, got = 302, response.status_code
        self.assertEqual(expected, got,
                "expected status code %s but got %s for decorated view with non-logged in user" \
                % (expected, got))

    def test_logged_in_notallowed(self):
        # set request to use staff user
        self.request.user = self.staff_user
        response = self.decorated(self.request)
        
        expected, got = 403, response.status_code
        self.assertEqual(expected, got,
                "expected status code %s but got %s for decorated view with logged-in user without perms" \
                % (expected, got))
        self.assertContains(response, "permission denied", status_code=403,
                msg_prefix="response contains content from 403.html template fixture")

    def test_logged_in_allowed(self):
        # set request to use superuser account
        self.request.user = self.super_user
        response = self.decorated(self.request)
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
                "expected status code %s but got %s for decorated view with superuser" \
                % (expected, got))
        self.assertContains(response, "Hello, World",
            msg_prefix="response contains actual view content")

class UserPassesTest403_Test(TestCase):
    fixtures =  ['users']

    def setUp(self):
        self.request = HttpRequest()
        self.request.user = AnonymousUser()

        self.staff_user = User.objects.get(username='staff')
        self.super_user = User.objects.get(username='super')

        self._template_dirs = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            path.join(path.dirname(path.abspath(__file__)), 'fixtures'),
        )

        # decorate simple view above for testing
        self.login_url = '/my/login/page'
        decorator = user_passes_test_with_403(lambda u: u.username == 'staff')
        self.decorated = decorator(simple_view)

    def tearDown(self):
        # restore any configured template dirs
        settings.TEMPLATE_DIRS = self._template_dirs

    def test_function_wrapping(self):
        self.assertEqual(self.decorated.__doc__, simple_view.__doc__,
            "decorated method docstring matches original method docstring")
        self.assertEqual(self.decorated.__name__, simple_view.__name__,
            "decorated method name matches original method name")

    def test_logged_in_allowed(self):
        # set request to use staff account
        self.request.user = self.staff_user
        response = self.decorated(self.request)
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
                "expected status code %s but got %s for decorated view with superuser" \
                % (expected, got))
        self.assertContains(response, "Hello, World",
            msg_prefix="response contains actual view content")
