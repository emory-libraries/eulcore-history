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
            wnn = xmlmap.XPathString('wacky_node_name')

class ExistQueryTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_TEST_COLLECTION

    FIXTURE_ONE = '''
        <root id="one">
            <name>one</name>
            <description>this one has one one</description>
            <wacky_node_name>a</wacky_node_name>
        </root>
    '''
    FIXTURE_TWO = '''
        <root id="abc">
            <name>two</name>
            <description>this one only has two</description>
        </root>
    '''
    FIXTURE_THREE = '''
        <root id="xyz">
            <name>three</name>
            <description>third!</description>
        </root>
    '''

    def setUp(self):
        self.db = ExistDB(server_url=settings.EXISTDB_SERVER_URL)
        self.db.createCollection(self.COLLECTION, True)

        self.db.load(self.FIXTURE_ONE, self.COLLECTION + '/f1.xml', True)
        self.db.load(self.FIXTURE_TWO, self.COLLECTION + '/f2.xml', True)
        self.db.load(self.FIXTURE_THREE, self.COLLECTION + '/f3.xml', True)

        self.qs = QuerySet(using=self.db, collection=self.COLLECTION, model=QueryTestModel)

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

    def test_count(self):
        self.assertEqual(3, self.qs.count(), "queryset count returns 3")

    def test_getitem(self):        
        # what is default sort order? is this test reliable?
        self.assertEqual("one", self.qs[0].name)
        self.assertEqual("two", self.qs[1].name)
        self.assertEqual("three", self.qs[2].name)

    def test_getitem_typeerror(self):
        self.assertRaises(TypeError, self.qs.__getitem__, "foo")

    def test_getitem_indexerror(self):
        self.assertRaises(IndexError, self.qs.__getitem__, -1)
        self.assertRaises(IndexError, self.qs.__getitem__, 23)

    def test_getslice(self):
        slice = self.qs[0:1]
        self.assert_(isinstance(slice, QuerySet))
        self.assert_(isinstance(slice[0], QueryTestModel))        
        self.assertEqual(2, slice.count())
        self.assertEqual('one', slice[0].name)

        slice = self.qs[1:2]
        self.assertEqual('two', slice[0].name)

    def test_filter(self):
        fqs = self.qs.filter(contains="two")
        self.assertEqual(1, fqs.count(), "count returns 1 when filtered - contains 'two'")
        self.assertEqual("two", fqs[0].name, "name matches filter")
        self.assertEqual(3, self.qs.count(), "main queryset remains unchanged by filter")

    def test_filter_field(self):
        fqs = self.qs.filter(name="one")
        self.assertEqual(1, fqs.count(), "count returns 1 when filtered on name = 'one' (got %s)"
            % self.qs.count())
        self.assertEqual("one", fqs[0].name, "name matches filter")
        self.assertEqual(3, self.qs.count(), "main queryset unchanged by filter")

    def test_filter_field_xpath(self):
        fqs = self.qs.filter(id="abc")
        self.assertEqual(1, fqs.count(), "count returns 1 when filtered on @id = 'abc' (got %s)"
            % self.qs.count())
        self.assertEqual("two", fqs[0].name, "name returned is correct for id filter")
        self.assertEqual(3, self.qs.count(), "main queryset unchanged by filter")

    def test_filter_field_contains(self):
        fqs = self.qs.filter(name__contains="o")
        self.assertEqual(2, fqs.count(),
            "should get 2 matches for filter on name contains 'o' (got %s)" % fqs.count())
        self.assertEqual(3, self.qs.count(), "main queryset unchanged by filter")

    def test_filter_field_startswith(self):
        fqs = self.qs.filter(name__startswith="o")
        self.assertEqual(1, fqs.count(),
            "should get 1 match for filter on name starts with 'o' (got %s)" % fqs.count())
        self.assertEqual(3, self.qs.count(), "main queryset unchanged by filter")

    def test_get(self):
        result  = self.qs.get(contains="two")
        self.assert_(isinstance(result, QueryTestModel), "get() with contains returns single result")
        self.assertEqual(result.name, "two", "result returned by get() has correct data")
        self.assertEqual(3, self.qs.count(), "main queryset unchanged by get()")

    def test_get_toomany(self):
        self.assertRaises(Exception, self.qs.get, contains="one")

    def test_get_nomatch(self):
        self.assertRaises(Exception, self.qs.get, contains="fifty-four")

    def test_get_byname(self):
        result  = self.qs.get(name="one")
        self.assert_(isinstance(result, QueryTestModel), "get() with contains returns single result")
        self.assertEqual(result.name, "one", "result returned by get() has correct data")
        self.assertEqual(3, self.qs.count(), "main queryset unchanged by get()")
    
    def test_filter_get(self):        
        result = self.qs.filter(contains="one").filter(name="two").get()
        self.assert_(isinstance(result, QueryTestModel))
        self.assertEqual("two", result.name, "filtered get() returns correct data")
        self.assertEqual(3, self.qs.count(), "main queryset unchanged by filtered get()")

    def test_reset(self):
        self.qs.filter(contains="two")
        self.qs.reset()
        self.assertEqual(3, self.qs.count(), "count should be 3 after filter is reset")

    def test_order_by(self):
        # element
        fqs = self.qs.order_by('name')
        self.assertEqual('one', fqs[0].name)
        self.assertEqual('three', fqs[1].name)
        self.assertEqual('two', fqs[2].name)
        self.assert_('order by ' not in self.qs.query.getQuery(), "main queryset unchanged by order_by()")
        # attribute
        fqs = self.qs.order_by('id')
        self.assertEqual('abc', fqs[0].id)
        self.assertEqual('one', fqs[1].id)
        self.assertEqual('xyz', fqs[2].id)

    def test_only(self):        
        self.qs.only(['name'])
        self.assert_('element name {' not in self.qs.query.getQuery(), "main queryset unchanged by only()")
        
        fqs = self.qs.filter(id='one').only(['name','id'])
        self.assert_(isinstance(fqs[0], PartialResultObject))
        self.assertTrue(hasattr(fqs[0], "name"))
        self.assertTrue(hasattr(fqs[0], "id"))
        self.assertFalse(hasattr(fqs[0], "description"))
        self.assertEqual('one', fqs[0].id)
        self.assertEqual('one', fqs[0].name)

        fqs = self.qs.filter(id='one').only(['wnn'])
        self.assertTrue(hasattr(fqs[0], "wnn"))
        self.assertEqual('a', fqs[0].wnn)

        

    def test_iter(self):
        for q in self.qs:
            self.assert_(isinstance(q, QueryTestModel))

    def test_also(self):        
        class SubqueryTestModel(xmlmap.XmlObject):
            name = xmlmap.XPathString('.')
            parent_id = xmlmap.XPathString('parent::root/@id')

        qs = QuerySet(using=self.db, collection=self.COLLECTION, model=SubqueryTestModel, xpath='//name')
        name = qs.also(['parent_id']).get(name__exact='two')
        self.assertEqual('abc', name.parent_id,
            "parent id set correctly when retuning at name level with also parent_id specified; should be 'abc', got '"
            + name.parent_id + "'")

    def test_getDocument(self):
      obj = self.qs.getDocument("f1.xml")
      self.assert_(isinstance(obj, QueryTestModel),
            "object returned by getDocument is instance of QueryTestModel")
      self.assertEqual("one", obj.name)

    def test_distinct(self):
        qs = QuerySet(using=self.db, collection=self.COLLECTION, xpath='//name')
        vals = qs.distinct()
        self.assertEqual('one', vals[0])
        self.assertEqual('two', vals[1])
        self.assertEqual('three', vals[2])


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
        xq.add_filter('.', 'contains', 'dog')
        self.assertEquals('/el[contains(., "dog")]', xq.getQuery())
        # filters are additive
        xq.add_filter('.', 'startswith', 'S')
        self.assertEquals('/el[contains(., "dog")][starts-with(., "S")]', xq.getQuery())

    def test_return_only(self):
        xq = Xquery(xpath='/el')
        xq.return_only({'myid':'@id', 'some_name':'name', 'first_letter':'substring(@n,1,1)'})
        self.assert_('return <el>' in xq._constructReturn('$n'))
        self.assert_('element myid {$n/string(@id)}' in xq._constructReturn('$n'))
        self.assert_('element some_name {$n/name/node()}' in xq._constructReturn('$n'))
        self.assert_('element first_letter {$n/substring(@n,1,1)}' in xq._constructReturn('$n'))
        self.assert_('</el>' in xq._constructReturn('$n'))

        xq = Xquery(xpath='/some/el/notroot')
        xq.return_only({'id':'@id'})
        self.assert_('return <notroot>' in xq._constructReturn('$n'))

    def test_return_also(self):
        xq = Xquery(xpath='/el')
        xq.return_also({'myid':'@id', 'some_name':'name'})
        self.assert_('$n/@*,' in xq._constructReturn('$n'))
        self.assert_('$n/node(),' in xq._constructReturn('$n'))
        self.assert_('element myid {$n/string(@id)},' in xq._constructReturn('$n'))


    def test_set_limits(self):
        # subsequence with xpath
        xq = Xquery(xpath='/el')
        xq.set_limits(low=0, high=4)
        self.assertEqual('subsequence(/el, 1, 5)', xq.getQuery())
        # subsequence with FLWR query
        xq.return_only({'name':'name'})
        self.assert_('subsequence(for $n in' in xq.getQuery())
        
        # additive limits
        xq = Xquery(xpath='/el')
        xq.set_limits(low=2, high=10)
        xq.set_limits(low=1, high=5)
        # FIXME: is this math right?
        self.assertEqual('subsequence(/el, 4, 5)', xq.getQuery())

        # no high specified
        xq = Xquery(xpath='/el')
        xq.set_limits(low=10)
        self.assertEqual('subsequence(/el, 11, )', xq.getQuery())

        # no low
        xq = Xquery(xpath='/el')
        xq.set_limits(high=15)
        self.assertEqual('subsequence(/el, 1, 16)', xq.getQuery())

    def test_clear_limits(self):
        xq = Xquery(xpath='/el')
        xq.set_limits(low=2, high=5)
        xq.clear_limits()
        self.assertEqual('/el', xq.getQuery())

    def test_distinct(self):
        # distinct-values
        xq = Xquery(xpath='/el')
        xq.distinct()
        self.assertEqual('distinct-values(/el)', xq.getQuery())


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

