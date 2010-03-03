import os
import unittest
from urlparse import urlsplit, urlunsplit

from django.conf import settings

import eulcore.existdb as nondjangoexistdb
from eulcore.django.existdb.db import *

# minimal testing here to confirm djangoified ExistDB works;
# more extensive tests are in test_existdb

class ExistDBTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_TEST_COLLECTION

    def setUp(self):
        self.db = ExistDB()        
        self.db.createCollection(self.COLLECTION, True)

        # rudimentary example of loading exist fixture from a file
        module_path = os.path.split(__file__)[0]
        fixture = os.path.join(module_path, 'exist_fixtures', 'hello.xml')
        self.db.load(open(fixture), self.COLLECTION + '/hello.xml', True)

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

    def test_init(self):
        self.assert_(isinstance(self.db, nondjangoexistdb.db.ExistDB))
        self.assert_(isinstance(self.db, ExistDB))
        
    def test_getDoc(self): 
        """Retrieve document loaded via file fixture"""
        xml = self.db.getDoc(self.COLLECTION + "/hello.xml")
        self.assertEquals(xml, "<hello>World</hello>")

    def test_failed_authentication_from_settings(self):
        """Check that initializing ExistDB with invalid django settings raises exception"""
        try:
            #passwords can be specified in localsettings.py
            # overwrite (and then restore) to ensure that authentication fails
            server_url = settings.EXISTDB_SERVER_URL

            parts = urlsplit(settings.EXISTDB_SERVER_URL)
            netloc = 'bad_user:bad_password@' + parts.hostname
            if parts.port:
                netloc += ':' + str(parts.port)
            bad_uri = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

            settings.EXISTDB_SERVER_URL = bad_uri
            test_db = ExistDB()
            self.assertRaises(nondjangoexistdb.db.ExistDBException,
                test_db.hasCollection, self.COLLECTION)
        finally:
            settings.EXISTDB_SERVER_URL = server_url

