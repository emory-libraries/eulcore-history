# file django/ldap/backends.py
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

"""This module implements basic double-bind LDAP authentication.

To use LDAP authentication in a Django app, include
:class:`eulcore.django.ldap.backends.LDAPBackend` in your
``AUTHENTICATION_BACKENDS`` setting, and add a few additional settings to
configure it::

    AUTH_LDAP_SERVER = 'ldaps://ldap.example.com'
    AUTH_LDAP_BASE_USER = 'cn=example,o=example.com'
    AUTH_LDAP_BASE_PASS = 's00p3rs33kr!t'
    AUTH_LDAP_SEARCH_SUFFIX = 'o=emory.edu'
    AUTH_LDAP_SEARCH_FILTER = '(uid=%s)'
    AUTH_LDAP_CHECK_SERVER_CERT = True
    AUTH_LDAP_CA_CERT_PATH = '/path/to/trusted/certs.pem'

In general, this should be all an application developer needs to do. For
those who want to tweak the functionality, several hooks have been
defined in :class:`LDAPBackend`.

Application developers at Emory University may want to look at the
:mod:`~eulcore.django.emory_ldap` module, which adds Emory-specific
features and LDAP attribute mappings. Non-Emory users may want to look at
that module for examples of how they might tweak the code for their own
implementations.
"""


from django.conf import settings
from django.contrib.auth.models import User, SiteProfileNotAvailable
from django.core.exceptions import ObjectDoesNotExist
from ldap.filter import escape_filter_chars
import ldap

# originally inspired by http://www.carthage.edu/webdev/?p=12

cert_path = getattr(settings, 'AUTH_LDAP_CA_CERT_PATH', '')
if cert_path:
    ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, cert_path)
check_cert = getattr(settings, 'AUTH_LDAP_CHECK_SERVER_CERT', True)
if not check_cert:
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)


def map_fields(model, source, **kwargs):
    """Copy values from a source dict to a model object. For each keyword
    argument specified, interpret the name as a model attribute name and the
    value as a source index. If the value is in the source dict, copy it to
    the named model attribute. Used as a helper to copy LDAP fields to model
    objects."""

    for model_field_name, source_field_name in kwargs.items():
        if source_field_name in source:
            values = source[source_field_name]
            if values:
                setattr(model, model_field_name, values[0])


# to login via ldap, add 'eulcore.django.ldap.backends.LDAPBackend' to your
# AUTHENTICATION_BACKENDS in settings.py.
class LDAPBackend(object):
    """A Django authentication backend for double-bind LDAP authentication."""

    USER_MODEL = User
    """The Django Model to create for each user. Defaults to
    :class:`django.contrib.auth.models.User`. The backend finds or creates
    one of these for each user it sees."""

    _server = None

    @property
    def server(self):
        'Initialize LDAPServer instance only when actually needed, then cache it.'
        if self._server is None:
            self._server = self.get_server(getattr(settings, 'AUTH_LDAP_BASE_USER', None),
                                      getattr(settings, 'AUTH_LDAP_BASE_PASS', None))
        return self._server

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
        username_results = self.server.find_username(username)
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
        """Set fields on the user model from a dictionary of LDAP attributes
        returned by the server. Called automatically by the backend while
        looking up a user. The keys of `extra_fields` are the LDAP
        attributes returned by the server for that user. The values are
        arrays of values included in the response."""
        map_fields(user, extra_fields,
            first_name='givenName',
            last_name='sn',
            email='mail')
        pass

    def update_user_profile_fields(self, profile, extra_fields):
        """Set fields on the user profile model from a dictionary of LDAP
        attributes returned by the server. Called automatically by the
        backend while looking up a user, but only if the
        ``AUTH_PROFILE_MODULE`` setting is set and this user already has a
        profile. The keys of `extra_fields` are the LDAP attributes returned
        by the server for that user. The values are arrays of values
        included in the response."""
        pass


class LDAPServer(object):
    def __init__(self, user_dn=None, password=None):
        self.server = ldap.initialize(settings.AUTH_LDAP_SERVER)
        self.server.protocol_version = ldap.VERSION3
        self.server.simple_bind_s(user_dn, password)

    def find_username(self, username):
        filter = settings.AUTH_LDAP_SEARCH_FILTER % (escape_filter_chars(username),)
        return self.server.search_s(settings.AUTH_LDAP_SEARCH_SUFFIX, ldap.SCOPE_SUBTREE, filter, ['*'])
