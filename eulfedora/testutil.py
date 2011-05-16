# file eulfedora/testutil.py
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
Custom test-runner with Fedora environment setup / teardown for all tests.

To use, configure as test runner in your Django settings::

   TEST_RUNNER = 'eulfedora.testutil.FedoraTestSuiteRunner'
   
"""


import logging

import unittest2 as unittest
from django.conf import settings
from django.core.management import call_command
from django.test.simple import DjangoTestSuiteRunner

from eulfedora.server import Repository, init_pooled_connection

logger = logging.getLogger(__name__)


class FedoraTestResult(unittest.TextTestResult):
    _stored_default_fedora_root = None
    _stored_default_fedora_pidspace = None

    def startTestRun(self):
        self._use_test_fedora()

    def stopTestRun(self):
        self._restore_fedora_root()

    def _use_test_fedora(self):
        self._stored_default_fedora_root = getattr(settings, "FEDORA_ROOT", None)
        self._stored_default_fedora_pidspace = getattr(settings, "FEDORA_PIDSPACE", None)

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
        self.remove_test_objects()
        # run syncrepo to load any content models or fixtures
        # - pass any test fedora credentials to syncrepo
        test_user = getattr(settings, 'FEDORA_TEST_USER', None)
        test_pwd = getattr(settings, 'FEDORA_TEST_PASSWORD', None)
        call_command('syncrepo', username=test_user, password=test_pwd)

    def _restore_fedora_root(self):
        # if there was a pidspace configured, clean up any test objects
        msg = ''
        if self._stored_default_fedora_pidspace is not None:
            self.remove_test_objects()
            msg += "Restoring Fedora pidspace: %s" % self._stored_default_fedora_pidspace
            settings.FEDORA_PIDSPACE = self._stored_default_fedora_pidspace        
        if self._stored_default_fedora_root is not None:
            msg += "Restoring Fedora root: %s" % self._stored_default_fedora_root
            settings.FEDORA_ROOT = self._stored_default_fedora_root
            # re-initialize pooled connection with restored fedora root
            init_pooled_connection()
        if msg:
            print '\n', msg

    def remove_test_objects(self):
        # remove any leftover test object before or after running tests
        # NOTE: This method expects to be called only when FEDORA_PIDSPACE has been
        # switched to a test pidspace

        # use test fedora credentials if they are set
        repo = Repository(root=getattr(settings, 'FEDORA_TEST_ROOT', None),
                          username=getattr(settings, 'FEDORA_TEST_USER', None),
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


class FedoraTextTestRunner(unittest.TextTestRunner):

    def __init__(self, *args, **kwargs):
        super(FedoraTextTestRunner, self).__init__(resultclass=FedoraTestResult, *args, **kwargs)

class FedoraTestSuiteRunner(DjangoTestSuiteRunner):
    
    def run_suite(self, suite, **kwargs):
        return FedoraTextTestRunner(verbosity=self.verbosity, failfast=self.failfast).run(suite)
