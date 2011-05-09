# file django/fedora/server.py
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

import warnings

from django.conf import settings
from eulcore.fedora import server, util
from eulcore.django.fedora import cryptutil

_connection = None

def init_pooled_connection(fedora_root=None):
    '''Initialize pooled connection for use with :class:`Repository`.

    :param fedora_root: base fedora url to use for connection.  If not specified,
        uses FEDORA_ROOT from django settings
    '''
    global _connection
    if fedora_root is None:
        fedora_root = settings.FEDORA_ROOT
    _connection = util.RelativeServerConnection(fedora_root)

init_pooled_connection()

class Repository(server.Repository):
    """Connect to a Fedora Repository based on configuration in ``settings.py``.

    This class is a simple wrapper to initialize :class:`eulcore.fedora.server.Repository`,
    based on Fedora connection parameters in a Django settings file.  If username
    and password are specified, they will override fedora credentials configured
    in Django settings.

    If a request object is passed in and the user is logged in, this
    class will look for credentials in the session, as set by
    :meth:`~eulcore.django.fedora.views.login_and_store_credentials_in_session`
    (see method documentation for more details and potential security
    risks).

    Order of precedence for credentials:
        
        * If a request object is passed in and user credentials are
          available in the session, that will be used first.
        * Explicit username and password parameters will be used next. 
        * If none of these options are available, fedora credentials
          will be set in django settings will be used.

    
    """
    def __init__(self, username=None, password=None, request=None):
        if request is not None and request.user.is_authenticated() and \
           FEDORA_PASSWORD_SESSION_KEY in request.session:
                username = request.user.username
                password = cryptutil.decrypt(request.session[FEDORA_PASSWORD_SESSION_KEY])            
        else:
            if username is None and hasattr(settings, 'FEDORA_USER'):
                username = settings.FEDORA_USER
                # look for FEDORA_PASSWORD first
                if password is None and hasattr(settings, 'FEDORA_PASSWORD'):
                    password = settings.FEDORA_PASSWORD
                # then look for FEDORA_PASS, but warn if it is present
                elif password is None and hasattr(settings, 'FEDORA_PASS'):
                    password = settings.FEDORA_PASS
                    # this method should no longer be needed - default pid logic moved to DigitalObject
                    warnings.warn("""For security reasons, you should use FEDORA_PASSWORD instead of FEDORA_PASS for Fedora credentials in your django settings.  The FEDORA_PASS setting is deprecated.""",
                      DeprecationWarning)

        super(Repository, self).__init__(_connection, username, password)

        if hasattr(settings, 'FEDORA_PIDSPACE'):
            self.default_pidspace = settings.FEDORA_PIDSPACE


# session key for storing a user password that will be used for Fedora access
# - used here and in eulcore.django.fedora.views
FEDORA_PASSWORD_SESSION_KEY = 'eulfedora_password'

