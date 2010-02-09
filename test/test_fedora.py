#!/usr/bin/env python

import os
import unittest
from eulcore.fedora import Repository

REPO_ROOT = 'https://dev11.library.emory.edu:8643/fedora/'
REPO_USER = 'fedoraAdmin'
REPO_PASS = 'fedoraAdmin'

PIDSPACE = 'python-eulcore-test'
FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')

class TestFedora(unittest.TestCase):

    def setUp(self):
        self.repo = Repository(REPO_ROOT, REPO_USER, REPO_PASS)

    def loadFixture(self, fname):
        fname = os.path.join(FIXTURE_ROOT, fname)
        with open(fname) as f:
            return f.read()

    def testIngestWithoutPid(self):
        object = self.loadFixture('basic-object.foxml')
        pid = self.repo.ingest(object)
        self.assertTrue(pid)
        self.repo.purge_object(pid)


if __name__ == '__main__':
    runner = unittest.TextTestRunner
    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass
    unittest.main(testRunner=runner)
