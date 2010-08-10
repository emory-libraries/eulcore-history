# file django\fedora\__init__.py
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

from django.conf import settings
from django.core.management import call_command

from eulcore.django.testsetup import starting_tests, finished_tests
from eulcore.django.fedora.server import Repository

_stored_default_fedora_root = None
_stored_default_fedora_pidspace = None

def _use_test_fedora(sender, **kwargs):
    global _stored_default_fedora_root
    global _stored_default_fedora_pidspace
    
    _stored_default_fedora_root = getattr(settings, "FEDORA_ROOT", None)
    _stored_default_fedora_pidspace = getattr(settings, "FEDORA_PIDSPACE", None)

    if getattr(settings, "FEDORA_TEST_ROOT", None):
        settings.FEDORA_ROOT = settings.FEDORA_TEST_ROOT
        print "Switching to test Fedora: %s" % settings.FEDORA_ROOT        
    else:
        print "FEDORA_TEST_ROOT is not configured in settings; tests will run against %s" % \
            settings.FEDORA_ROOT

    if getattr(settings, "FEDORA_TEST_PIDSPACE", None):
        settings.FEDORA_PIDSPACE = settings.FEDORA_TEST_PIDSPACE
    elif getattr(settings, "FEDORA_PIDSPACE", None):
        settings.FEDORA_PIDSPACE = "%s-test" % settings.FEDORA_PIDSPACE
    print "Using Fedora pidspace: %s" % settings.FEDORA_PIDSPACE

    # run syncrepo to load any content models or fixtures
    call_command('syncrepo')

def _restore_fedora_root(sender, **kwargs):
    global _stored_default_fedora_root
    global _stored_default_fedora_pidspace

    # if there was a pidspace configured, clean up any test objects
    if _stored_default_fedora_pidspace is not None:
        repo = Repository()
        test_objects = repo.find_objects(pid__contains='%s*' % settings.FEDORA_PIDSPACE)
        count = 0
        for obj in test_objects:
            repo.purge_object(obj.pid, "removing test object")
            count += 1
        if count:
            print "Removed %s test object(s) with pidspace %s" % (count, settings.FEDORA_PIDSPACE)
        print "Restoring Fedora pidspace: %s" % _stored_default_fedora_pidspace
        settings.FEDORA_PIDSPACE = _stored_default_fedora_pidspace        
    if _stored_default_fedora_root is not None:
        print "Restoring Fedora root: %s" % _stored_default_fedora_root
        settings.FEDORA_ROOT = _stored_default_fedora_root


starting_tests.connect(_use_test_fedora)
finished_tests.connect(_restore_fedora_root)
