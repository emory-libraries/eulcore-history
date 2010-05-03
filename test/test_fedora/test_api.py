#!/usr/bin/env python

from test_fedora.base import FedoraTestCase, REPO_ROOT_NONSSL, REPO_USER, REPO_PASS, TEST_PIDSPACE
from eulcore.fedora.api import API_A_LITE, REST_API
from testcore import main


class TestAPI_A_LITE(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestAPI_A_LITE, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.api_a = API_A_LITE(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)

    def testDescribeRepository(self):
        desc = self.api_a.describeRepository()
        self.assert_('<repositoryName>' in desc)
        self.assert_('<repositoryVersion>' in desc)
        self.assert_('<adminEmail>' in desc)

    def testGetDatastreamDissemination(self):
        dc = self.api_a.getDatastreamDissemination(self.pid, "DC")
        self.assert_('<oai_dc:dc' in dc)
        self.assert_('<dc:title>A partially-prepared test object</dc:title>' in dc)
        self.assert_('<dc:description>' in dc)
        self.assert_('<dc:identifier>%s</dc:identifier>' % self.pid in dc)

class TestREST_API(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestREST_API, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.rest_api = REST_API(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)

    def test_getObjectHistory(self):
        history = self.rest_api.getObjectHistory(self.pid)
        print history

if __name__ == '__main__':
    main()
