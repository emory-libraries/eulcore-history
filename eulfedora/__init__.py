# file eulfedora/__init__.py
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

# TODO: cleanup/revise documentation here

"""
:mod:`eulcore.django.fedora` is a Django-aware extension of
:mod:`eulcore.fedora`.

When you create an instance of :class:`~eulcore.django.fedora.server.Repository`,
it will automatically configure the repository connection based on Django
settings, using the configuration names documented below.

If you are writing unit tests that use this module, you should include
:mod:`eulcore.django.testsetup` in your ``INSTALLED_APPS``.
:mod:`eulcore.django.fedora` uses the pre- and post- test signals defined
by :mod:`~eulcore.django.testsetup` to temporarily switch the configured
fedora root to the test fedora instance. Any :class:`~eulcore.django.fedora.server.Repository`
instances created within the tests will automatically connect to the test collection.
If you have a test pidspace configured, that will be used for the default pidspace
when creating test objects; if you have a pidspace but not a test pidspace,
the set to use a pidspace of 'yourpidspace-test' for the duration of the tests.
Any objects in the test pidspace will be removed from the Fedora instance after
the tests finish.

Projects that use this module should include the following settings in their
``settings.py``::

    # Fedora Repository settings
    FEDORA_ROOT = 'http://fedora.host.name:8080/fedora/'
    FEDORA_USER = 'user'
    FEDORA_PASSWORD = 'password'
    FEDORA_PIDSPACE = 'changeme'
    FEDORA_TEST_ROOT = 'http://fedora.host.name:8180/fedora/'
    FEDORA_TEST_PIDSPACE = 'testme'

If username and password are not specified, the Repository instance will be
initialized without credentials.  If pidspace is not specified, the Repository
will use the default pidspace for the configured Fedora instance.

Projects that need unit test setup and clean-up tasks (syncrepo and
test object removal) to access Fedora with different credentials than
the configured Fedora credentials should use the following settings::

    FEDORA_TEST_USER = 'testuser'
    FEDORA_TEST_PASSWORD = 'testpassword'

"""


__version_info__ = (0, 1, 'dev')

# Dot-connect all but the last. Last is dash-connected if not None.
__version__ = '.'.join([ str(i) for i in __version_info__[:-1] ])
if __version_info__[-1] is not None:
    __version__ += ('-%s' % (__version_info__[-1],))
