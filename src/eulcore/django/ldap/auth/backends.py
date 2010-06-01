from django.contrib.auth.models import User
from eulcore.django.ldap import LDAPServer, INVALID_CREDENTIALS

# originally inspired by http://www.carthage.edu/webdev/?p=12

def map_fields(model, source, **kwargs):
    for model_field_name, source_field_name in kwargs.items():
        if source_field_name in source:
            values = source[source_field_name]
            if values:
                setattr(model, model_field_name, values[0])


# to login via ldap, add 'eulcore.ldap.auth.backends.LDAPBackend' to your
# AUTHENTICATION_BACKENDS in settings.py.
class LDAPBackend(object):
    USER_MODEL = User

    def __init__(self):
        self.server = self.get_server(settings.AUTH_LDAP_BASE_USER, 
                                      settings.AUTH_LDAP_BASE_PASS)

    def get_server(self, user_dn, password):
        return LDAPServer(user_dn, password)

    def authenticate(self, username=None, password=None):
        user_dn, user = self.server.find_user(username)

        # use a new LDAPServer in case binding causes access/permissions
        # problems for the root one.
        try:
            self.get_server(user_dn, password)
            # LDAPServer will raise an exception on auth failure, so if we
            # created the LDAPServer then we succeeded.
            return user
        except INVALID_CREDENTIALS:
            return None

        return user

    def get_user(self, user_id):
        try:
            return USER_MODEL.objects.get(pk=user_id)
        except USER_MODEL.DoesNotExist:
            return None

    def find_user(self, username):
        user_dn, user_fields = self.server.find_username(username)
        if user_dn is None:
            return None, None

        user, created = USER_MODEL.objects.get_or_create(username=username)
        user.set_unusable_password()
        self.update_user_fields(user, user_fields)
        user.save()

        return user_dn, user

    def update_user_fields(self, user, extra_fields):
        # overide/extend this to map LDAP fields to model fields
        map_fields(user, extra_fields,
            first_name='givenName',
            last_name='sn',
            email='mail')
        pass


class LDAPServer(object):
    def __init__(self, user_dn=None, password=None):
        self.server = ldap.initialize(settings.AUTH_LDAP_SERVER)
        self.server.protocol_version = ldap.VERSION3
        self.server.simple_bind_s(user_dn, password)

    def find_username(self, username):
        filter = settings.AUTH_LDAP_SEARCH_FILTER % (ldap.filter.escape_filter_chars(username),)
        result_data = self.server.search_s(settings.AUTH_LDAP_SEARCH_SUFFIX, ldap.SCOPE_SUBTREE, filter, ['*'])

        # If the user does not exist in LDAP, Fail.
        if (len(result_data) != 1):
            return None, None
        user_dn, user_fields = result_data[0]

        return user_dn, user_fields
