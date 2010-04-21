import os
import unittest
from eulcore.fedora.server import Repository

REPO_ROOT = 'https://dev11.library.emory.edu:8643/fedora/'
REPO_ROOT_NONSSL = 'http://dev11.library.emory.edu:8280/fedora/'
REPO_USER = 'fedoraAdmin'
REPO_PASS = 'fedoraAdmin'

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), 'fixtures')
def fixture_path(fname):
    return os.path.join(FIXTURE_ROOT, fname)

def load_fixture_data(fname):
    with open(fixture_path(fname)) as f:
        return f.read()

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
        return load_fixture_data(fname)

    def ingestFixture(self, fname):
        object = load_fixture_data(fname)
        pid = self.repo.ingest(object)
        if pid:
            # we'd like this always to be true. if ingest fails we should
            # throw an exception. that probably hasn't been thoroughly
            # tested yet, though, so we'll check it until it has been.
            self.fedora_fixtures_ingested.append(pid)
