from django.test import TestCase
from eulcore.django.emory_ldap.backends import EmoryLDAPBackend
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
