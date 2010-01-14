from django.contrib.auth.models import User
from eulcore.django.ldap import LDAPServer, INVALID_CREDENTIALS

# originally inspired by http://www.carthage.edu/webdev/?p=12

# to login via ldap, add 'eulcore.ldap.auth.backends.LDAPBackend' to your
# AUTHENTICATION_BACKENDS in settings.py.
class LDAPBackend(object):
    def __init__(self, serverclass=None):
        if serverclass is None:
            serverclass = LDAPServer
        self.serverclass = serverclass
        self.server = serverclass()

    def authenticate(self, username=None, password=None):
        user_dn, user = self.server.find_user(username)
        if not self.ldap_authenticate(user_dn, password):
            return None

        return user

    def ldap_authenticate(self, user_dn, password):
        # use a new LDAPServer in case binding causes access/permissions
        # problems for the root one.
        try:
            self.serverclass(user_dn, password)
            # LDAPServer will raise an exception on auth failure, so if we
            # created the LDAPServer then we succeeded.
            return True
        except INVALID_CREDENTIALS:
            return False

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
