#!/usr/bin/env python

import unittest
from urlparse import urlsplit, urlunsplit

from eulcore.existdb import db
from testcore import main

EXISTDB_SERVER_URL = "http://kamina.library.emory.edu:8080/exist/xmlrpc"
EXISTDB_ROOT_COLLECTION = '/eulcore'
# NOTE: currently, for full-text query tests to work, test collection should be named /test/something
#       a system collection named /db/system/config/db/test should exist and be writable by guest
EXISTDB_TEST_COLLECTION = '/test' + EXISTDB_ROOT_COLLECTION

class ExistDBTest(unittest.TestCase):
    COLLECTION = EXISTDB_TEST_COLLECTION

    def setUp(self):
        self.db = db.ExistDB(server_url=EXISTDB_SERVER_URL)        
        self.db.createCollection(self.COLLECTION, True)
	
        self.db.load('<hello>World</hello>', self.COLLECTION + '/hello.xml', True)

        xml = '<root><element name="one">One</element><element name="two">Two</element><element name="two">Three</element></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test.xml', True)

        xml = '<root><field name="one">One</field><field name="two">Two</field><field name="three">Three</field><field name="four">Four</field></root>'
        self.db.load(xml, self.COLLECTION + '/xqry_test2.xml', True)

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

    def test_getDoc(self):
        """Test retrieving a full document from eXist"""
        xml = self.db.getDoc(self.COLLECTION + "/hello.xml")
        self.assertEquals(xml, "<hello>World</hello>")

    def test_remove(self):
        "Test removing a full document from eXist"
        result = self.db.remove(self.COLLECTION + "/hello.xml")
        self.assertTrue(result)
        # attempting to retrieve the deleted file should cause an exception
        self.assertRaises(Exception, self.db.getDoc, self.COLLECTION + "/hello.xml")
        
    def test_hasCollection(self):
        """Check collections can be found in eXist"""
        #test collection created in setup
        self.assertTrue(self.db.hasCollection(self.COLLECTION), "hasCollection failed to return true for existing collection")
        #test bad collection that does not exist
        self.assertFalse(self.db.hasCollection("/nonexistingCollecton"), "hasCollection failed to return false for non-existing collection")

    def test_getCollectionDescription(self):
        """Test retrieving information about a collection in eXist"""
        info = self.db.getCollectionDescription(self.COLLECTION)

        self.assertEqual("/db" + self.COLLECTION, info['name'],
            "collection name returned (expected '/db/%s', got '%s'" % (self.COLLECTION, info['name']))
        self.assertEqual("guest", info['owner'],
            "collection owner returned (expected 'guest', got %s" % info['owner'])
        # untested - group, created, permissions
        self.assertEqual(3, len(info['documents']), "collection has 3 documents (3 test documents loaded)")
        self.assertEqual([], info['collections'], "collection has no subcollections")

        # attempting to describe a collection that isn't in the db
        self.assertRaises(db.ExistDBException, self.db.getCollectionDescription,
            "bogus_collection")

    def test_createCollection(self):
        """Test creating new collections in eXist"""
        #create new collection
        self.assertTrue(self.db.createCollection(self.COLLECTION + "/new_collection"),
            "failed to create new collection")

        #attempt create collection again expects ExistDBException
        self.assertRaises(db.ExistDBException,
            self.db.createCollection, self.COLLECTION + "/new_collection")

        #create new collection again with over_write = True
        self.assertTrue(self.db.createCollection(self.COLLECTION + "/new_collection", True),
            "failed to create new collection with over_write")

    def test_removeCollection(self):
        """Test removing collections from eXist"""
        #attempt to remove non-existent collection expects ExistDBException
        self.assertRaises(db.ExistDBException,
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
        self.assertRaises(db.ExistDBException,
            self.db.query, xqry)

    def test_query_with_no_result(self):
        """Test xquery with no results"""
        xqry = 'for $x in collection("/db%s")/root/field where $x/@name="notfound" return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry)

        self.assertTrue(qres.hits is not None)
        self.assertTrue(qres.count is not None)

        self.assertFalse(qres.hits, 0)
        self.assertEquals(qres.count, 0)
        self.assertEquals(qres.start, None)

        self.assertFalse(qres.hasMore())
        self.assertFalse(qres.results)


    def test_executeQuery(self):
        """Test executeQuery & dependent functions (querySummary, getHits, retrieve)"""
        xqry = 'for $x in collection("/db%s")/root/element where $x/@name="two" return $x' % (self.COLLECTION, )        
        result_id = self.db.executeQuery(xqry)
        self.assert_(isinstance(result_id, int), "executeQuery returns integer result id")

        # run querySummary on result from executeQuery
        summary = self.db.querySummary(result_id)
        self.assertEqual(2, summary['hits'], "querySummary returns correct hit count of 2")
        self.assert_(isinstance(summary['queryTime'], int), "querySummary return includes int queryTime")
        # any reasonable way to check what is in the documents summary info?
        # documents should be an array of arrays - document name, id, and # hits

        # getHits on result
        hits = self.db.getHits(result_id)
        self.assert_(isinstance(hits, int), "getHits returns integer hit count")
        self.assertEqual(2, hits, "getHits returns correct count of 2")

        # retrieve first result
        result = self.db.retrieve(result_id, 0)
        self.assertEqual('<element name="two">Two</element>', result,
                "retrieve index 0 returns first element with @name='two'")
        # retrieve second result
        result = self.db.retrieve(result_id, 1)
        self.assertEqual('<element name="two">Three</element>', result,
                "retrieve index 0 returns first element with @name='two'")

    def test_executeQuery_noresults(self):
        """Test executeQuery & dependent functions (querySummary, getHits, retrieve) - xquery with no results"""
        xqry = 'collection("/db%s")/root/element[@name="bogus"]' % (self.COLLECTION, )
        result_id = self.db.executeQuery(xqry)
        # run querySummary on result from executeQuery
        summary = self.db.querySummary(result_id)
        self.assertEqual(0, summary['hits'], "querySummary returns hit count of 0")
        self.assertEqual([], summary['documents'], "querySummary document list is empty")
        
        # getHits 
        hits = self.db.getHits(result_id)
        self.assertEqual(0, hits, "getHits returns correct count of 0 for query with no match")

        # retrieve non-existent result
        self.assertRaises(db.ExistDBException, self.db.retrieve, result_id, 0)
        

    def test_executeQuery_bad_xquery(self):
        """Check that an invalid xquery raises an exception"""
        #invalid xqry missing "
        xqry = 'collection("/db%s")//root/element[@name=two"]' % (self.COLLECTION, )
        self.assertRaises(db.ExistDBException, self.db.executeQuery, xqry)

    def test_releaseQuery(self):
        xqry = 'collection("/db%s")/root/element[@name="two"]' % (self.COLLECTION, )
        result_id = self.db.executeQuery(xqry)
        self.db.releaseQueryResult(result_id)
        # attempting to get data from a result that has been released should cause an error
        self.assertRaises(Exception, self.db.getHits, result_id)

    def test_load_invalid_xml(self):
        """Check that loading invaliid xml raises an exception"""
        xml = '<root><element></root>'
        self.assertRaises(db.ExistDBException,
            self.db.load, xml, self.COLLECTION + 'invalid.xml')

    def test_failed_authentication(self):
        """Check that connecting with invalid user credentials raises an exception"""
        parts = urlsplit(EXISTDB_SERVER_URL)
        netloc = 'bad_user:bad_password@' + parts.hostname
        if parts.port:
            netloc += ':' + str(parts.port)
        bad_uri = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

        test_db = db.ExistDB(server_url=bad_uri)
        self.assertRaises(db.ExistDBException,
                test_db.hasCollection, self.COLLECTION)

    def test_hasMore(self):
        """Test hasMore, show_to, and show_from based on numbers in xquery result"""
        xqry = 'for $x in collection("/db%s")//root/field return $x' % (self.COLLECTION, )
        qres = self.db.query(xqry, how_many=2, start=1)
        self.assertTrue(qres.hasMore())
        self.assertEquals(qres.show_from, 1)
        self.assertEquals(qres.show_to, 2)

        qres = self.db.query(xqry, how_many=2, start=3)
        self.assertFalse(qres.hasMore())
        self.assertEquals(qres.show_from, 3)
        self.assertEquals(qres.show_to, 4)

        qres = self.db.query(xqry, how_many=2, start=4)
        self.assertFalse(qres.hasMore())
        self.assertEquals(qres.show_from, 4)
        self.assertEquals(qres.show_to, 4)


    def test_configCollectionName(self):
        self.assertEqual("/db/system/config/db/foo", self.db._configCollectionName("foo"))
        self.assertEqual("/db/system/config/db/foo", self.db._configCollectionName("/foo"))
        self.assertEqual("/db/system/config/db/foo", self.db._configCollectionName("/foo/"))
        self.assertEqual("/db/system/config/db/foo/bar", self.db._configCollectionName("/foo/bar"))

    def test_collectionIndexPath(self):
        self.assertEqual("/db/system/config/db/foo/collection.xconf", self.db._collectionIndexPath("foo"))

    def test_loadCollectionIndex(self):
        """Test loading a collection index config file to the system config collection."""
        self.db.loadCollectionIndex(self.COLLECTION, "<collection/>")
        self.assert_(self.db.hasCollection(self.db._configCollectionName(self.COLLECTION)))
        xml = self.db.getDoc(self.db._collectionIndexPath(self.COLLECTION))
        self.assertEquals(xml, "<collection/>")

        # reload with overwrite disabled - should cause an exception
        self.assertRaises(db.ExistDBException, self.db.loadCollectionIndex,
            self.COLLECTION, "<collection/>", False)

        # clean up
        self.db.removeCollection(self.db._configCollectionName( self.COLLECTION))

    def test_removeCollectionIndex(self):
        """Test removing a collection index config file from the system config collection."""
        self.db.loadCollectionIndex(self.COLLECTION, "<collection/>")
        
        self.assertTrue(self.db.removeCollectionIndex(self.COLLECTION))
        # collection config file should be gone         # FIXME: better way to test missing file?
        # NOTE: apparently getDoc behaves differently when neither doc nor collection exist (?)
        #   does not throw an exception when document's collection does not exist
        self.assertFalse(self.db.getDoc(self.db._collectionIndexPath(self.COLLECTION)),
            "collection index configuration should not be in eXist")
        self.assertFalse(self.db.hasCollection(self.db._configCollectionName(self.COLLECTION)),
            "config collection should have been removed from eXist")

        self.db.loadCollectionIndex(self.COLLECTION, "<collection/>")
        self.db.createCollection(self.db._configCollectionName(self.COLLECTION) + "/subcollection")
        self.assertTrue(self.db.removeCollectionIndex(self.COLLECTION))
        # NOTE: getDoc on nonexistent file actually raises exception here because collection exists (?)
        self.assertRaises(Exception, self.db.getDoc, self.db._collectionIndexPath(self.COLLECTION))
        self.assertTrue(self.db.hasCollection(self.db._configCollectionName(self.COLLECTION)),
            "config collection should not be removed when it contains documents")

        # clean up
        self.db.removeCollection(self.db._configCollectionName( self.COLLECTION))



if __name__ == '__main__':
    main()
