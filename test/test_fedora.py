#!/usr/bin/env python

import os
import unittest
from eulcore.fedora import Repository

REPO_ROOT = 'https://dev11.library.emory.edu:8643/fedora/'
REPO_USER = 'fedoraAdmin'
REPO_PASS = 'fedoraAdmin'

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')

class FedoraTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.fedora_fixtures_ingested = []

    def setUp(self):
        self.repo = Repository(REPO_ROOT, REPO_USER, REPO_PASS)
        fixtures = getattr(self, 'fixtures', [])
        for fixture in fixtures:
            self.ingestFixture(fixture)

    def tearDown(self):
        for pid in self.fedora_fixtures_ingested:
            self.repo.purge_object(pid)

    def loadFixtureData(self, fname):
        fname = os.path.join(FIXTURE_ROOT, fname)
        with open(fname) as f:
            return f.read()

    def ingestFixture(self, fname):
        object = self.loadFixtureData(fname)
        pid = self.repo.ingest(object)
        if pid:
            # we'd like this always to be true. if ingest fails we should
            # throw an exception. that probably hasn't been thoroughly
            # tested yet, though, so we'll check it until it has been.
            self.fedora_fixtures_ingested.append(pid)


class TestBasicFedoraFunctionality(FedoraTestCase):
    def testGetNextPID(self):
        pid = self.repo.get_next_pid()
        self.assertTrue(pid)

        PID_SPACE = 'python-eulcore-test'
        pid = self.repo.get_next_pid(namespace=PID_SPACE)
        self.assertTrue(pid.startswith(PID_SPACE))

        COUNT = 3
        pids = self.repo.get_next_pid(namespace=PID_SPACE, count=COUNT)
        self.assertEqual(len(pids), COUNT)
        for pid in pids:
            self.assertTrue(pid.startswith(PID_SPACE))


    def testIngestWithoutPid(self):
        object = self.loadFixtureData('basic-object.foxml')
        pid = self.repo.ingest(object)
        self.assertTrue(pid)
        self.repo.purge_object(pid)

    # FIXME: how can we test logMessage arg to ingest and purge


if __name__ == '__main__':
    runner = unittest.TextTestRunner
    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass
    unittest.main(testRunner=runner)
