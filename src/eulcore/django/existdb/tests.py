import os
import unittest
from eulcore.django.existdb.db import *
from django.conf import settings

class ExistDBTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_ROOT_COLLECTION

    def setUp(self):
        self.db = ExistDB()        
        self.db.createCollection(self.COLLECTION, True)

        module_path = os.path.split(__file__)[0]
        fixture = os.path.join(module_path, 'exist_fixtures', 'hello.xml')
        self.db.load(open(fixture), self.COLLECTION + '/hello.xml', True)

        xml = '<root><element name="one">One</element><element name="two">Two</element><element name="two">Three</element></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test.xml', True)

        xml = '<root><field name="one">One</field><field name="two">Two</field><field name="three">Three</field><field name="four">Four</field></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test2.xml', True)

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

    def test_getDoc(self):
        xml = self.db.getDoc(self.COLLECTION + "/hello.xml")
        self.assertEquals(xml, "<hello>World</hello>")

    def test_hasCollection(self):
        #test collection created in setup
        self.assertTrue(self.db.hasCollection(self.COLLECTION), "hasCollection failed to return true for existing collection")
        #test bad collection that does not exist
        self.assertFalse(self.db.hasCollection("/nonexistingCollecton"), "hasCollection failed to return false for non-existing collection")

    def test_createCollection(self):
        #create new collection
        self.assertTrue(self.db.createCollection(self.COLLECTION + "/new_collection"),
            "failed to create new collection")

        #attempt create collection again expects ExistDBException
        self.assertRaises(ExistDBException,
            self.db.createCollection, self.COLLECTION + "/new_collection")

        #create new collection again with over_write = True
        self.assertTrue(self.db.createCollection(self.COLLECTION + "/new_collection", True),
            "failed to create new collection with over_write")

    def test_removeCollection(self):
        #attempt to remove non-existent collection expects ExistDBException
        self.assertRaises(ExistDBException,
            self.db.removeCollection, self.COLLECTION + "/new_collection")

        #create collection to test removal
        self.db.createCollection(self.COLLECTION + "/new_collection")
        self.assertTrue(self.db.removeCollection(self.COLLECTION + "/new_collection"), "removeCollection failed to remove existing collection")

    def test_query(self):
        xqry = 'for $x in collection("/db%s")//root/element where $x/@name="two" return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry)
        self.assertEquals(qres.hits, 2)
        self.assertEquals(qres.start, 1)
        self.assertEquals(qres.count, 2)

        self.assertEquals(qres.results[0].xpath('string()'), 'Two')
        self.assertEquals(qres.results[1].xpath('string()'), 'Three')

    def test_query_bad_xqry(self):
        #invalid xqry missing "
        xqry = 'for $x in collection("/db%s")//root/element where $x/@name=two" return $x' % (self.COLLECTION, )
        self.assertRaises(ExistDBException,
            self.db.query, xqry)

    def test_query_with_no_result(self):
        xqry = 'for $x in collection("/db%s")/root/field where $x/@name="notfound" return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry)
        self.assertEquals(qres.hits, None)
        self.assertEquals(qres.start, None)
        self.assertEquals(qres.count, None)
        self.assertFalse(qres.hasMore())

        self.assertFalse(qres.results) #empty list evaluates to false

    def test_load_invalid_xml(self):
        xml = '<root><element></root>'
        self.assertRaises(ExistDBException,
            self.db.load, xml, self.COLLECTION + 'invalid.xml')

    def test_failed_authentication(self):
        try:
            #passwords are specified in localsettings.py we will overwrite
            #and then restore to ensure that authentication fails
            server_url = settings.EXISTDB_SERVER_URL
            settings.EXISTDB_SERVER_URL = settings.EXISTDB_SERVER_PROTOCOL + \
                settings.EXISTDB_SERVER_USER + ":bad_password@" + settings.EXISTDB_SERVER_HOST

            test_db = ExistDB()
            self.assertRaises(ExistDBException,
                test_db.hasCollection, self.COLLECTION)
        finally:
            settings.EXISTDB_SERVER_URL = server_url

    def test_hasMore(self):
        xqry = 'for $x in collection("/db%s")//root/field return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry=xqry, how_many=2, start=1)
        self.assertTrue(qres.hasMore())
        self.assertEquals(qres.show_from, 1)
        self.assertEquals(qres.show_to, 2)

        qres = self.db.query(xqry=xqry, how_many=2, start=3)
        self.assertFalse(qres.hasMore())
        self.assertEquals(qres.show_from, 3)
        self.assertEquals(qres.show_to, 4)

        qres = self.db.query(xqry=xqry, how_many=2, start=4)
        self.assertFalse(qres.hasMore())
        self.assertEquals(qres.show_from, 4)
        self.assertEquals(qres.show_to, 4)
