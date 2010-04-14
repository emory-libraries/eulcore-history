#!/usr/bin/env python

import unittest
from test_fedora.base import FedoraTestCase, load_fixture_data
from testcore import main

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
        object = load_fixture_data('basic-object.foxml')
        pid = self.repo.ingest(object)
        self.assertTrue(pid)
        self.repo.purge_object(pid)

        # test ingesting with log message
        pid = self.repo.ingest(object, "this is my test ingest message")
        # ingest message is stored in AUDIT datastream
        # - can currently only be accessed by retrieving entire object xml
        self.assertTrue("this is my test ingest message" in self.repo.rest_api.getObjectXML(pid))
        self.repo.purge_object(pid, "removing test ingest object")
        # FIXME: how can we test logMessage arg to purge?
        #  -- have no idea where log message is actually stored... (if anywhere)

    def testFindObjects(self):
        object = load_fixture_data('basic-object.foxml')
        pid = self.repo.ingest(object)

        objects = list(self.repo.find_objects(ownerId='tester'))
        # should find test object
        self.assertEqual(objects[0].pid, pid)

        self.repo.purge_object(pid)


if __name__ == '__main__':
    main()
