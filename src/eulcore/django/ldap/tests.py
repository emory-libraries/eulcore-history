from unittest import TestCase
from django.contrib.auth.models import User
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

    def find_usernames(self, username):
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

