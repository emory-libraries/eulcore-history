import os
import unittest
from eulcore import xmlmap
from eulcore.fedora.api import ApiFacade
from eulcore.fedora.server import Repository

#FEDORA_ROOT = 'https://dev11.library.emory.edu:8643/fedora/'
#FEDORA_ROOT_NONSSL = 'http://dev11.library.emory.edu:8280/fedora/'
# fedora3.3
#FEDORA_ROOT = 'https://dev11.library.emory.edu:8843/fedora/'
#FEDORA_ROOT_NONSSL = 'http://dev11.library.emory.edu:8480/fedora/'
# fedora3.4
FEDORA_ROOT = 'https://dev11.library.emory.edu:8943/fedora/'
FEDORA_ROOT_NONSSL = 'http://dev11.library.emory.edu:8580/fedora/'
FEDORA_USER = 'fedoraAdmin'
FEDORA_PASS = 'fedoraAdmin'
FEDORA_PIDSPACE = 'eulcoretest'

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')
def fixture_path(fname):
    return os.path.join(FIXTURE_ROOT, fname)

def load_fixture_data(fname):
    with open(fixture_path(fname)) as f:
        return f.read()

class _MinimalFoxml(xmlmap.XmlObject):
    pid = xmlmap.StringField('@PID')

class FedoraTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.fedora_fixtures_ingested = []

    def setUp(self):
        self.repo = Repository(FEDORA_ROOT, FEDORA_USER, FEDORA_PASS)
        # NOTE: queries require RI flush=True or test objects will not show up in RI
        self.repo.risearch.RISEARCH_FLUSH_ON_QUERY = True
        self.opener = self.repo.opener
        self.api = ApiFacade(self.opener)
        fixtures = getattr(self, 'fixtures', [])
        for fixture in fixtures:
            self.ingestFixture(fixture)

    def tearDown(self):
        for pid in self.fedora_fixtures_ingested:
            self.repo.purge_object(pid)

    def getNextPid(self):
        pidspace = getattr(self, 'pidspace', None)
        return self.repo.get_next_pid(namespace=pidspace)

    def loadFixtureData(self, fname):
        data = load_fixture_data(fname)
        # if pidspace is specified, get a new pid from fedora and set it as the pid in the xml 
        if hasattr(self, 'pidspace'):
            xml = xmlmap.load_xmlobject_from_string(data, _MinimalFoxml)            
            xml.pid = self.getNextPid()
            return xml.serialize()
        else:
            return data

    def ingestFixture(self, fname):
        object = self.loadFixtureData(fname)
        pid = self.repo.ingest(object)
        if pid:
            # we'd like this always to be true. if ingest fails we should
            # throw an exception. that probably hasn't been thoroughly
            # tested yet, though, so we'll check it until it has been.
            self.append_test_pid(pid)

    def append_test_pid(self, pid):
            self.fedora_fixtures_ingested.append(pid)
