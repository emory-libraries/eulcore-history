from django.conf import settings
from django.contrib.auth.models import User, SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
import ldap

# originally inspired by http://www.carthage.edu/webdev/?p=12

cert_path = getattr(settings, 'AUTH_LDAP_CA_CERT_PATH', '')
if cert_path:
    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, cert_path)
check_cert = getattr(settings, 'AUTH_LDAP_CHECK_SERVER_CERT', True)
if not check_cert:
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)


def map_fields(model, source, **kwargs):
    for model_field_name, source_field_name in kwargs.items():
        if source_field_name in source:
            values = source[source_field_name]
            if values:
                setattr(model, model_field_name, values[0])


# to login via ldap, add 'eulcore.ldap.backends.LDAPBackend' to your
# AUTHENTICATION_BACKENDS in settings.py.
class LDAPBackend(object):
    USER_MODEL = User

    def __init__(self):
        self.server = self.get_server(getattr(settings, 'AUTH_LDAP_BASE_USER', None),
                                      getattr(settings, 'AUTH_LDAP_BASE_PASS', None))

    def get_server(self, user_dn, password):
        return LDAPServer(user_dn, password)

    def authenticate(self, username=None, password=None):
        user_dn, user = self.find_user(username)
        if user_dn is None or user is None:
            return None

        # use a new LDAPServer in case binding causes access/permissions
        # problems for the root one.
        try:
            self.get_server(user_dn, password)
            # LDAPServer will raise an exception on auth failure, so if we
            # created the LDAPServer then we succeeded.
            return user
        except ldap.INVALID_CREDENTIALS:
            return None

        return user

    def get_user(self, user_id):
        try:
            return self.USER_MODEL.objects.get(pk=user_id)
        except self.USER_MODEL.DoesNotExist:
            return None

    def find_user(self, username):
        username_results = self.server.find_usernames(username)
        # If the user does not exist in LDAP, of if somehow there are
        # multiple matches, fail.
        if len(username_results) != 1:
            return None, None

        user_dn, user_fields = username_results[0]
        user, created = self.USER_MODEL.objects.get_or_create(username=username)
        user.set_unusable_password()
        self.update_user_fields(user, user_fields)
        user.save()

        try:
            profile = user.get_profile()
            self.update_user_profile_fields(profile, user_fields)
            profile.save()
        except (ObjectDoesNotExist, SiteProfileNotAvailable):
            pass # no profile to update.

        return user_dn, user

    def update_user_fields(self, user, extra_fields):
        # overide/extend this to map LDAP fields to model fields
        map_fields(user, extra_fields,
            first_name='givenName',
            last_name='sn',
            email='mail')
        pass

    def update_user_profile_fields(self, profile, extra_fields):
        # overide/extend this to map LDAP fields to user profile fields
        pass


class LDAPServer(object):
    def __init__(self, user_dn=None, password=None):
        self.server = ldap.initialize(settings.AUTH_LDAP_SERVER)
        self.server.protocol_version = ldap.VERSION3
        self.server.simple_bind_s(user_dn, password)

    def find_username(self, username):
        filter = settings.AUTH_LDAP_SEARCH_FILTER % (ldap.filter.escape_filter_chars(username),)
        return self.server.search_s(settings.AUTH_LDAP_SEARCH_SUFFIX, ldap.SCOPE_SUBTREE, filter, ['*'])
