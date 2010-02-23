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

    # FIXME: how can we test logMessage arg to ingest and purge


if __name__ == '__main__':
    main()
