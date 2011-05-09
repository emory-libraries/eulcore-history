# file django/fedora/__init__.py
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


import logging

from django.conf import settings
from django.core.management import call_command

from eulcore.django.testsetup import starting_tests, finished_tests
from eulcore.django.fedora.server import Repository, init_pooled_connection

_stored_default_fedora_root = None
_stored_default_fedora_pidspace = None

logger = logging.getLogger(__name__)

def _use_test_fedora(sender, **kwargs):
    global _stored_default_fedora_root
    global _stored_default_fedora_pidspace
    
    _stored_default_fedora_root = getattr(settings, "FEDORA_ROOT", None)
    _stored_default_fedora_pidspace = getattr(settings, "FEDORA_PIDSPACE", None)

    if getattr(settings, "FEDORA_TEST_ROOT", None):
        settings.FEDORA_ROOT = settings.FEDORA_TEST_ROOT
        print "Switching to test Fedora: %s" % settings.FEDORA_ROOT
        # pooled fedora connection gets initialized before this change;
        # re-initialize connection with new fedora root configured
        init_pooled_connection()
    else:
        print "FEDORA_TEST_ROOT is not configured in settings; tests will run against %s" % \
            settings.FEDORA_ROOT

    if getattr(settings, "FEDORA_TEST_PIDSPACE", None):
        settings.FEDORA_PIDSPACE = settings.FEDORA_TEST_PIDSPACE
    elif getattr(settings, "FEDORA_PIDSPACE", None):
        settings.FEDORA_PIDSPACE = "%s-test" % settings.FEDORA_PIDSPACE
    print "Using Fedora pidspace: %s" % settings.FEDORA_PIDSPACE
    
    # remove any test objects left over from a previous test run
    remove_test_objects()
    # run syncrepo to load any content models or fixtures
    # - pass any test fedora credentials to syncrepo
    test_user = getattr(settings, 'FEDORA_TEST_USER', None)
    test_pwd = getattr(settings, 'FEDORA_TEST_PASSWORD', None)
    call_command('syncrepo', username=test_user, password=test_pwd)

def _restore_fedora_root(sender, **kwargs):
    global _stored_default_fedora_root
    global _stored_default_fedora_pidspace

    # if there was a pidspace configured, clean up any test objects
    if _stored_default_fedora_pidspace is not None:
        remove_test_objects()
        print "Restoring Fedora pidspace: %s" % _stored_default_fedora_pidspace
        settings.FEDORA_PIDSPACE = _stored_default_fedora_pidspace        
    if _stored_default_fedora_root is not None:
        print "Restoring Fedora root: %s" % _stored_default_fedora_root
        settings.FEDORA_ROOT = _stored_default_fedora_root
        # re-initialize pooled connection with restored fedora root
        init_pooled_connection()

def remove_test_objects():
    # remove any leftover test object before or after running tests
    # NOTE: This method expects to be called only when FEDORA_PIDSPACE has been
    # switched to a test pidspace
    
    # use test fedora credentials if they are set
    repo = Repository(username=getattr(settings, 'FEDORA_TEST_USER', None),
                            password=getattr(settings, 'FEDORA_TEST_PASSWORD', None))
    test_objects = repo.find_objects(pid__contains='%s:*' % settings.FEDORA_PIDSPACE)
    count = 0
    for obj in test_objects:
        # if objects are unexpectedly not being cleaned up, pid/label may help
        # to isolate which test is creating the leftover objects
        logger.info('Purging test object %s - %s' % (obj.pid, obj.label))
        repo.purge_object(obj.pid, "removing test object")
        count += 1
    if count:
        print "Removed %s test object(s) with pidspace %s" % (count, settings.FEDORA_PIDSPACE)


starting_tests.connect(_use_test_fedora)
finished_tests.connect(_restore_fedora_root)
