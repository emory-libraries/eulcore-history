# file django\ldap\tests.py
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

import ldap
from django.contrib.auth.models import User
from django.test import TestCase
from eulcore.django.ldap.backends import LDAPBackend

class TestBackend(LDAPBackend):
    '''An LDAPBackend that overrides only the bare minimum necessary to mock
    out the actual LDAP protocol communication.
    '''

    def __init__(self, *args, **kwargs):
        self._server = MockServer()
        super(TestBackend, self).__init__(*args, **kwargs)

    def get_server(self, *args, **kwargs):
        self._server.mock_authentication_stub(*args, **kwargs)
        return self._server


class MockServer(object):
    def __init__(self):
        # set these manually in tests to control the results of calls on
        # this simple mock object.
        self.auth_exception = None
        self.find_results = []

    def mock_authentication_stub(self, username, password):
        if self.auth_exception is not None:
            raise self.auth_exception

    def find_username(self, username):
        return self.find_results


class LDAPBackendTest(TestCase):
    def setUp(self):
        self.backend = TestBackend()
        self.server = self.backend._server

    def testAuthenticateNewUser(self):
        # no extra fields for now
        self.server.find_results = [('uid=test_user,o=example.com', {})]
        self.server.auth_exception = None

        user = self.backend.authenticate('test_user', 'good_password')
        self.assertEqual('test_user', user.username)

        # and verify the user is in the db
        user = User.objects.get(username='test_user')
        self.assertEqual('test_user', user.username)

    def testAuthenticateExistingUser(self):
        user = User.objects.create(username='test_user')
        user.save()
        uid = user.id

        self.server.find_results = [('uid=test_user,o=example.com', {})]
        self.server.auth_exception = None

        user = self.backend.authenticate('test_user', 'good_password')
        self.assertEqual('test_user', user.username)
        self.assertEqual(uid, user.id)

    def testAuthenticatePopulatesUserData(self):
        self.server.find_results = [('uid=test_user,o=example.com', {
                    'givenName': ['Test'],
                    'sn': ['User'],
                    'mail': ['test_user@example.com'],
                }),
            ]
        self.server.auth_exception = None
        
        user = self.backend.authenticate('test_user', 'good_password')
        self.assertEqual('test_user', user.username)
        self.assertEqual('Test', user.first_name)
        self.assertEqual('User', user.last_name)
        self.assertEqual('test_user@example.com', user.email)

    def testAcceptExtraFields(self):
        '''Test that we can handle unrecognized LDAP fields from the server.'''
        self.server.find_results = [('uid=test_user,o=example.com', {
                    'mail': ['test_user@example.com'],
                    'foo': ['abc'],
                    'bar': ['def'],
                }),
            ]
        self.server.auth_exception = None

        user = self.backend.authenticate('test_user', 'good_password')
        self.assertEqual('test_user', user.username)
        self.assertEqual('test_user@example.com', user.email)

    def testNoSuchUser(self):
        self.server.find_results = []
        self.server.auth_exception = None

        user = self.backend.authenticate('test_user', 'good_password')
        self.assertTrue(user is None)

    def testBadPassword(self):
        self.server.find_results = [('uid=test_user,o=example.com', {})]
        self.server.auth_exception = ldap.INVALID_CREDENTIALS

        user = self.backend.authenticate('test_user', 'bad_password')
        self.assertTrue(user is None)

