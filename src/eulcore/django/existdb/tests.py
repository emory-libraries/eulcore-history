# file django/existdb/tests.py
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

from lxml import etree
import os
import unittest
from urlparse import urlsplit, urlunsplit

from django.conf import settings

from eulcore import xmlmap
from eulcore.django.existdb.db import ExistDB
from eulcore.django.existdb.manager import Manager
from eulcore.django.existdb.models import XmlModel
from eulcore.django.existdb.templatetags.existdb import exist_matches
import eulcore.existdb as nondjangoexistdb
from eulcore.existdb.db import EXISTDB_NAMESPACE
from eulcore.xmlmap  import XmlObject

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


class ExistMatchTestCase(unittest.TestCase):
# test exist_match template tag explicitly
    SINGLE_MATCH = """<abstract>Pitts v. <exist:match xmlns:exist="%s">Freeman</exist:match>
school desegregation case files</abstract>""" % EXISTDB_NAMESPACE
    MULTI_MATCH = """<title>Pitts v. <exist:match xmlns:exist="%(ex)s">Freeman</exist:match>
<exist:match xmlns:exist="%(ex)s">school</exist:match> <exist:match xmlns:exist="%(ex)s">desegregation</exist:match>
case files</title>""" % {'ex': EXISTDB_NAMESPACE}

    def setUp(self):
        self.content = XmlObject(etree.fromstring(self.SINGLE_MATCH))   # placeholder

    def test_single_match(self):
        self.content.node = etree.fromstring(self.SINGLE_MATCH)
        format = exist_matches(self.content)
        self.assert_('Pitts v. <span class="exist-match">Freeman</span>'
            in format, 'exist:match tag converted to span for highlighting')

    def test_multiple_matches(self):
        self.content.node = etree.fromstring(self.MULTI_MATCH)
        format = exist_matches(self.content)
        self.assert_('Pitts v. <span class="exist-match">Freeman</span>'
            in format, 'first exist:match tag converted')
        self.assert_('<span class="exist-match">school</span> <span class="exist-match">desegregation</span>'
            in format, 'second and third exist:match tags converted')


