#!/usr/bin/env python
import os
import unittest
from eulcore.existdb.db import *


class settings:
    EXISTDB_SERVER_PROTOCOL = "http://"
    EXISTDB_SERVER_HOST     = "kamina.library.emory.edu:8080/exist/xmlrpc"
    EXISTDB_SERVER_USER     = ""
    EXISTDB_SERVER_PWD      = ""
    #EXISTDB_SERVER_URL      = EXISTDB_SERVER_PROTOCOL + EXISTDB_SERVER_USER + ":" \
    #    + EXISTDB_SERVER_PWD + "@" + EXISTDB_SERVER_HOST
    EXISTDB_SERVER_URL      = EXISTDB_SERVER_PROTOCOL + EXISTDB_SERVER_HOST
    EXISTDB_ROOT_COLLECTION = "/eulcore"
    EXISTDB_TEST_COLLECTION = "/eulcore_test"


class ExistDBTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_TEST_COLLECTION

    def setUp(self):
        self.db = ExistDB(server_url=settings.EXISTDB_SERVER_URL)        
        self.db.createCollection(self.COLLECTION, True)
	
        self.db.load('<hello>World</hello>', self.COLLECTION + '/hello.xml', True)

        xml = '<root><element name="one">One</element><element name="two">Two</element><element name="two">Three</element></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test.xml', True)

        xml = '<root><field name="one">One</field><field name="two">Two</field><field name="three">Three</field><field name="four">Four</field></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test2.xml', True)

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

    def test_getDoc(self):
        """Test loading a full document from eXist"""
        xml = self.db.getDoc(self.COLLECTION + "/hello.xml")
        self.assertEquals(xml, "<hello>World</hello>")

    def test_hasCollection(self):
        """Check collections can be found in eXist"""
        #test collection created in setup
        self.assertTrue(self.db.hasCollection(self.COLLECTION), "hasCollection failed to return true for existing collection")
        #test bad collection that does not exist
        self.assertFalse(self.db.hasCollection("/nonexistingCollecton"), "hasCollection failed to return false for non-existing collection")

    def test_createCollection(self):
        """Test creating new collections in eXist"""
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
        """Test removing collections from eXist"""
        #attempt to remove non-existent collection expects ExistDBException
        self.assertRaises(ExistDBException,
            self.db.removeCollection, self.COLLECTION + "/new_collection")

        #create collection to test removal
        self.db.createCollection(self.COLLECTION + "/new_collection")
        self.assertTrue(self.db.removeCollection(self.COLLECTION + "/new_collection"), "removeCollection failed to remove existing collection")

    def test_query(self):
        """Test xquery results with hits & count"""
        xqry = 'for $x in collection("/db%s")//root/element where $x/@name="two" return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry)
        self.assertEquals(qres.hits, 2)
        self.assertEquals(qres.start, 1)
        self.assertEquals(qres.count, 2)

        self.assertEquals(qres.results[0].xpath('string()'), 'Two')
        self.assertEquals(qres.results[1].xpath('string()'), 'Three')

    def test_query_bad_xqry(self):
        """Check that an invalid xquery raises an exception"""
        #invalid xqry missing "
        xqry = 'for $x in collection("/db%s")//root/element where $x/@name=two" return $x' % (self.COLLECTION, )
        self.assertRaises(ExistDBException,
            self.db.query, xqry)

    def test_query_with_no_result(self):
        """Test xquery with no results"""
        xqry = 'for $x in collection("/db%s")/root/field where $x/@name="notfound" return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry)
        self.assertEquals(qres.hits, None)
        self.assertEquals(qres.start, None)
        self.assertEquals(qres.count, None)
        self.assertFalse(qres.hasMore())

        self.assertFalse(qres.results) #empty list evaluates to false

    def test_load_invalid_xml(self):
        """Check that loading invaliid xml raises an exception"""
        xml = '<root><element></root>'
        self.assertRaises(ExistDBException,
            self.db.load, xml, self.COLLECTION + 'invalid.xml')

    def test_failed_authentication(self):
        """Check that connecting with invaliid user credentials raises an exception"""
        test_db = ExistDB(server_url=settings.EXISTDB_SERVER_PROTOCOL + \
                          settings.EXISTDB_SERVER_USER + ":bad_password@" + \
                          settings.EXISTDB_SERVER_HOST)
        self.assertRaises(ExistDBException,
                  test_db.hasCollection, self.COLLECTION)

    def test_hasMore(self):
        """Test hasMore, show_to, and show_from based on numbers in xquery result"""
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



if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner)
