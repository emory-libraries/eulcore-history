# file django\existdb\tests.py
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

import os
import unittest
from urlparse import urlsplit, urlunsplit

from django.conf import settings

from eulcore import xmlmap
from eulcore.django.existdb.db import ExistDB
from eulcore.django.existdb.manager import Manager
from eulcore.django.existdb.models import XmlModel
import eulcore.existdb as nondjangoexistdb

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
        
    def test_getDocument(self):
        """Retrieve document loaded via file fixture"""
        xml = self.db.getDocument(self.COLLECTION + "/hello.xml")
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


class PartingBase(xmlmap.XmlObject):
    '''A plain XmlObject comparable to how one might be defined in
    production code.'''
    exclamation = xmlmap.StringField('exclamation')
    target = xmlmap.StringField('target')

class Parting(XmlModel, PartingBase):
    '''An XmlModel can derive from an XmlObject to incorporate its
    fields.'''
    objects = Manager('/parting')

class ModelTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_TEST_COLLECTION

    def setUp(self):
        self.db = ExistDB()        
        self.db.createCollection(self.COLLECTION, True)

        module_path = os.path.split(__file__)[0]
        fixture = os.path.join(module_path, 'exist_fixtures', 'goodbye-english.xml')
        self.db.load(open(fixture), self.COLLECTION + '/goodbye-english.xml', True)
        fixture = os.path.join(module_path, 'exist_fixtures', 'goodbye-french.xml')
        self.db.load(open(fixture), self.COLLECTION + '/goodbye-french.xml', True)

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

    def test_manager(self):
        partings = Parting.objects.all()
        self.assertEquals(2, partings.count())
