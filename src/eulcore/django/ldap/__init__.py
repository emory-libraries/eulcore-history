import ldap
import ldap.filter
from django.conf import settings
from django.contrib.auth.models import User
from ldap import INVALID_CREDENTIALS

# originally inspired by http://www.carthage.edu/webdev/?p=12

cert_path = getattr(settings, 'AUTH_LDAP_CA_CERT_PATH', '')
if cert_path:
    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, cert_path)
check_cert = getattr(settings, 'AUTH_LDAP_CHECK_SERVER_CERT', True)
if not check_cert:
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)


class LDAPServer(object):
    def __init__(self, user_dn=None, password=None):
        self.server = ldap.initialize(settings.AUTH_LDAP_SERVER)
        self.server.protocol_version = ldap.VERSION3

        if user_dn is None:
            user_dn = settings.AUTH_LDAP_BASE_USER
        if password is None:
            password = settings.AUTH_LDAP_BASE_PASS
            
        self.server.simple_bind_s(user_dn, password)

    def find_username(self, username):
        filter = settings.AUTH_LDAP_SEARCH_FILTER % (ldap.filter.escape_filter_chars(username),)
        result_data = self.server.search_s(settings.AUTH_LDAP_SEARCH_SUFFIX, ldap.SCOPE_SUBTREE, filter, ['*'])

        # If the user does not exist in LDAP, Fail.
        if (len(result_data) != 1):
            return None, None
        user_dn, user_fields = result_data[0]

        return user_dn, user_fields

    def find_user(self, username):
        user_dn, user_fields = self.find_username(username)
        if user_dn is None:
            return None, None

        user, created = User.objects.get_or_create(username=username)
        user.set_unusable_password()
        self.update_user_fields(user, user_fields)
        user.save()

        if hasattr(settings, 'AUTH_PROFILE_MODULE'):
            profile = user.get_profile()
            if profile is not None:
                self.update_user_profile_fields(profile, user_fields)
                profile.save()

        return user_dn, user

    def update_user_fields(self, user, extra_fields):
        pass

    def update_user_profile_fields(self, profile, extra_fields):
        pass

