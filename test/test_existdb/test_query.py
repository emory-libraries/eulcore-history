#!/usr/bin/env python

import unittest
from test_existdb.test_db import settings
from eulcore.existdb.db import ExistDB
from eulcore.existdb.query import QuerySet
import eulcore.xmlmap.core as xmlmap

class QueryTestModel(xmlmap.XmlObject):
            name = xmlmap.XPathString('name')
            description = xmlmap.XPathString('description')

class ExistQueryTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_TEST_COLLECTION

    FIXTURE_ONE = '''
        <root>
            <name>one</name>
            <description>this one has one one</description>
        </root>
    '''
    FIXTURE_TWO = '''
        <root>
            <name>two</name>
            <description>this one only has two</description>
        </root>
    '''    

    def setUp(self):
        self.db = ExistDB(server_url=settings.EXISTDB_SERVER_URL)
        self.db.createCollection(self.COLLECTION, True)

        self.db.load(self.FIXTURE_ONE, self.COLLECTION + '/f1.xml', True)
        
        self.db.load(self.FIXTURE_TWO, self.COLLECTION + '/f2.xml', True)

        self.qs = QuerySet(using=self.db, collection=self.COLLECTION, model=QueryTestModel)

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

    def test_count(self):
        self.assertEqual(2, self.qs.count(), "queryset count returns 2")

    def test_getitem(self):        
        # NOTE: default sort seems to be last-modified, so reverse order that they were saved
        self.assertEqual("two", self.qs[0].name)
        self.assertEqual("one", self.qs[1].name)

    def test_filter(self):
        self.qs.filter(contains="two")
        self.assertEqual(1, self.qs.count(), "count returns 1 when filtered - contains 'two'")
        self.assertEqual("two", self.qs[0].name, "name matches filter")

    def test_filter_field(self):
        self.qs.filter(name="one")
        self.assertEqual(1, self.qs.count(), "count returns 1 when filtered on name = 'one' (got %s)"
            % self.qs.count())
        self.assertEqual("one", self.qs[0].name, "name matches filter")

    def test_filter_field_contains(self):
        self.assertEqual(2, self.qs.filter(name__contains="o").count(),
            "should get 2 matches for filter on name contains 'o' (got %s)" % self.qs.count())

    def test_filter_field_startswith(self):        
        self.assertEqual(1, self.qs.filter(name__startswith="o").count(),
            "should get 1 match for filter on name starts with 'o' (got %s)" % self.qs.count())

    def test_get(self):
        result  = self.qs.get(contains="two")
        self.assert_(isinstance(result, QueryTestModel), "get() with contains returns single result")
        self.assertEqual(result.name, "two", "result returned by get() has correct data")

    def test_get_toomany(self):
        self.assertRaises(Exception, self.qs.get, contains="one")

    def test_get_nomatch(self):
        self.assertRaises(Exception, self.qs.get, contains="three")


    def test_get_byname(self):
        result  = self.qs.get(name="one")
        self.assert_(isinstance(result, QueryTestModel), "get() with contains returns single result")
        self.assertEqual(result.name, "one", "result returned by get() has correct data")
    
    def test_filter_get(self):        
        result = self.qs.filter(contains="one").filter(name="two").get()
        self.assert_(isinstance(result, QueryTestModel))
        self.assertEqual("two", result.name, "filtered get() returns correct data")

    def test_reset(self):
        self.qs.filter(contains="two")
        self.qs.reset()
        self.assertEqual(2, self.qs.count(), "count should be 2 after filter is reset")

if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner)
