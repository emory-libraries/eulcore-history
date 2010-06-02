from django.test import TestCase
from eulcore.django.emory_ldap.backends import EmoryLDAPBackend
from eulcore.django.emory_ldap.management.commands import inituser
from eulcore.django.emory_ldap.models import EmoryLDAPUser
from eulcore.django.ldap.tests import MockServer

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
        user = EmoryLDAPUser(username='test_user')
        user.first_name = 'Test'
        user.last_name = 'User'
        self.assertEqual('Test User', user.get_full_name())

    def test_explicit_full_name(self):
        user = EmoryLDAPUser(username='test_user')
        user.first_name = 'Test'
        user.last_name = 'User'
        user.full_name = 'Frank Oz'
        self.assertEqual('Frank Oz', user.get_full_name())
        

class BackendTest(TestCase):
    def setUp(self):
        self.backend = TestBackend()
        self.server = self.backend._server

    def testEmoryUserFields(self):
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
        self.assertEqual('770-555-6789', user.phone)
        self.assertEqual('42', user.dept_num)
        self.assertEqual('Test User', user.full_name)
        self.assertEqual('Supreme Commander of Testing', user.title)
        self.assertEqual('3', user.employee_num)
        self.assertEqual('11', user.subdept_code)
        self.assertEqual('9', user.hr_id)
        self.assertTrue(user.is_staff)
 

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

        user = EmoryLDAPUser.objects.get(username='test_user')
        self.assertEqual('Test', user.first_name)
        self.assertEqual('User', user.last_name)
        self.assertEqual('test_user@example.com', user.email)
        self.assertEqual('Supreme Commander of Testing', user.title)
        self.assertTrue(user.is_staff)

    def testMissingUser(self):
        self.server.find_results = []

        self.command.handle('test_user')

        self.assertRaises(EmoryLDAPUser.DoesNotExist,
                EmoryLDAPUser.objects.get, username='test_user')
