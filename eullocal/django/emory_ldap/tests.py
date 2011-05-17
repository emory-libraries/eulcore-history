# file eullocal/django/emory_ldap/tests.py
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

from django.contrib.auth.models import User
from django.test import TestCase
from eullocal.django.emory_ldap.backends import EmoryLDAPBackend
from eullocal.django.emory_ldap.management.commands import inituser
from eullocal.django.ldap.tests import MockServer

class TestBackend(EmoryLDAPBackend):
    '''An EmoryLDAPBackend that overrides only the bare minimum necessary to mock
    out the actual LDAP protocol communication.
    '''

    def __init__(self, *args, **kwargs):
        self._server = MockServer()
        super(TestBackend, self).__init__(*args, **kwargs)

    def get_server(self, *args, **kwargs):
        self._server.mock_authentication_stub(*args, **kwargs)
        return self._server


class UserTest(TestCase):
    def test_implicit_full_name(self):
        user = User(username='test_user')
        user.first_name = 'Test'
        user.last_name = 'User'
        user.save()
        self.assertEqual('Test User', user.get_profile().get_full_name())

    def test_explicit_full_name(self):
        user = User(username='test_user')
        user.first_name = 'Test'
        user.last_name = 'User'
        user.save()

        profile = user.get_profile()
        profile.full_name = 'Frank Oz'
        self.assertEqual('Frank Oz', profile.get_full_name())
        

class BackendTest(TestCase):
    def setUp(self):
        self.backend = TestBackend()
        self.server = self.backend._server

    def testProfileFields(self):
        self.server.find_results = [('uid=test_user,o=example.com', {
                    'givenName': ['Test'],
                    'sn': ['User'],
                    'mail': ['test_user@example.com'],
                    'telephoneNumber': ['770-555-6789'],
                    'departmentNumber': ['42'],
                    'cn': ['Test User'],
                    'title': ['Supreme Commander of Testing'],
                    'employeeNumber': ['3'],
                    'emorysubdeptcode': ['11'],
                    'hremplid': ['9'],
                }),
            ]
        self.server.auth_exception = None
        
        user = self.backend.authenticate('test_user', 'good_password')
        self.assertEqual('test_user', user.username)
        self.assertEqual('Test', user.first_name)
        self.assertEqual('User', user.last_name)
        self.assertEqual('test_user@example.com', user.email)
        self.assertTrue(user.is_staff)

        profile = user.get_profile()
        self.assertEqual('770-555-6789', profile.phone)
        self.assertEqual('42', profile.dept_num)
        self.assertEqual('Test User', profile.full_name)
        self.assertEqual('Supreme Commander of Testing', profile.title)
        self.assertEqual('3', profile.employee_num)
        self.assertEqual('11', profile.subdept_code)
        self.assertEqual('9', profile.hr_id)
 

class TestInitUserCommand(inituser.Command):
    def __init__(self):
        super(TestInitUserCommand, self).__init__()
        self._backend = TestBackend()

    def get_backend(self):
        return self._backend


class InitUserTest(TestCase):
    def setUp(self):
        self.command = TestInitUserCommand()
        self.backend = self.command._backend
        self.server = self.backend._server

    def testExistingUser(self):
        self.server.find_results = [('uid=test_user,o=example.com', {
                    'givenName': ['Test'],
                    'sn': ['User'],
                    'mail': ['test_user@example.com'],
                    'title': ['Supreme Commander of Testing'],
                }),
            ]

        self.command.handle('test_user')

        user = User.objects.get(username='test_user')
        self.assertEqual('Test', user.first_name)
        self.assertEqual('User', user.last_name)
        self.assertEqual('test_user@example.com', user.email)
        self.assertTrue(user.is_staff)

        self.assertEqual('Supreme Commander of Testing', user.get_profile().title)

    def testMissingUser(self):
        self.server.find_results = []
        self.command.handle('test_user')
        self.assertRaises(User.DoesNotExist,
                User.objects.get, username='test_user')
