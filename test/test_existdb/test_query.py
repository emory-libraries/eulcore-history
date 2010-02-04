#!/usr/bin/env python

import unittest
from test_existdb.test_db import settings
from eulcore.existdb.db import ExistDB
from eulcore.existdb.query import QuerySet, Xquery, PartialResultObject
import eulcore.xmlmap.core as xmlmap

class QueryTestModel(xmlmap.XmlObject):
            id = xmlmap.XPathString('@id')
            name = xmlmap.XPathString('name')
            description = xmlmap.XPathString('description')

class ExistQueryTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_TEST_COLLECTION

    FIXTURE_ONE = '''
        <root id="one">
            <name>one</name>
            <description>this one has one one</description>
        </root>
    '''
    FIXTURE_TWO = '''
        <root id="abc">
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
        self.assertEqual(1, self.qs.filter(contains="two").count(), "count returns 1 when filtered - contains 'two'")
        self.assertEqual("two", self.qs.filter(contains="two")[0].name, "name matches filter")

    def test_filter_field(self):
        self.qs.filter(name="one")
        self.assertEqual(1, self.qs.filter(name="one").count(), "count returns 1 when filtered on name = 'one' (got %s)"
            % self.qs.count())
        self.assertEqual("one", self.qs.filter(name="one")[0].name, "name matches filter")

    def test_filter_field_xpath(self):
        self.qs.filter(id="abc")
        self.assertEqual(1, self.qs.filter(id="abc").count(), "count returns 1 when filtered on @id = 'abc' (got %s)"
            % self.qs.count())
        self.assertEqual("two", self.qs.filter(id="abc")[0].name, "name returned is correct for id filter")

    def test_filter_field_contains(self):
        fqs = self.qs.filter(name__contains="o")
        self.assertEqual(2, fqs.count(),
            "should get 2 matches for filter on name contains 'o' (got %s)" % fqs.count())

    def test_filter_field_startswith(self):
        fqs = self.qs.filter(name__startswith="o")
        self.assertEqual(1, fqs.count(),
            "should get 1 match for filter on name starts with 'o' (got %s)" % fqs.count())

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

    def test_order_by(self):
        fqs = self.qs.order_by('name')
        self.assertEqual('one', fqs[0].name)
        self.assertEqual('two', fqs[1].name)

    def test_order_by(self):
        fqs = self.qs.order_by('id')
        self.assertEqual('abc', fqs[0].id)
        self.assertEqual('one', fqs[1].id)

    def test_only(self):
        fqs = self.qs.filter(id='one').only(['name','id'])
        
        self.assert_(isinstance(fqs[0], PartialResultObject))
        self.assertTrue(hasattr(fqs[0], "name"))
        self.assertTrue(hasattr(fqs[0], "id"))
        self.assertFalse(hasattr(fqs[0], "description"))
        self.assertEqual('one', fqs[0].id)
        self.assertEqual('one', fqs[0].name)


class XqueryTest(unittest.TestCase):

    def test_defaults(self):
        xq = Xquery()
        self.assertEquals('/node()', xq.getQuery())

    def test_xpath(self):
        xq = Xquery(xpath='/path/to/el')
        self.assertEquals('/path/to/el', xq.getQuery())

    def test_coll(self):
        xq = Xquery(collection='myExistColl')
        self.assertEquals('collection("/db/myExistColl")/node()', xq.getQuery())

        xq = Xquery(xpath='/root/el', collection='/coll/sub')
        self.assertEquals('collection("/db/coll/sub")/root/el', xq.getQuery())

    def test_sort(self):
        xq = Xquery(collection="mycoll")        
        xq.sort('@id')
        self.assert_('order by $n/@id' in xq.getQuery())
        self.assert_('collection("/db/mycoll")' in xq.getQuery())

    def test_filters(self):
        xq = Xquery(xpath='/el')
        xq.add_filter('contains(., "dog")')
        self.assertEquals('/el[contains(., "dog")]', xq.getQuery())
        # filters are additive
        xq.add_filter('startswith(., "S")')
        self.assertEquals('/el[contains(., "dog")][startswith(., "S")]', xq.getQuery())

    def test_return_only(self):
        xq = Xquery(xpath='/el')
        xq.return_only(['@id', 'name'])
        self.assert_('return <el>' in xq._constructReturn('$n'))
        self.assert_('{$n/@id}' in xq._constructReturn('$n'))
        self.assert_('{$n/name}' in xq._constructReturn('$n'))
        self.assert_('</el>' in xq._constructReturn('$n'))

        xq = Xquery(xpath='/some/el/notroot')
        xq.return_only(['@id'])
        self.assert_('return <notroot>' in xq._constructReturn('$n'))


class PartialResultObjectTest(unittest.TestCase):
    xml = '''
    <root id="007">
         <name>James</name>
         <date>2010</date>
    </root>
    '''
    def test_init(self):
        partial = xmlmap.load_xmlobject_from_string(self.xml, PartialResultObject)
        self.assertEquals('James', partial.name)
        self.assertEquals('2010', partial.date)
        self.assertEquals('007', partial.id)



if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner)

