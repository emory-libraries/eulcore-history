#!/usr/bin/env python

from datetime import date

from test_fedora.base import FedoraTestCase, load_fixture_data, FEDORA_ROOT_NONSSL, FEDORA_PIDSPACE
from eulfedora.rdfns import model as modelns
from eulfedora.models import DigitalObject
from eulfedora.server import Repository, UnrecognizedQueryLanguage

from testcore import main

class TestBasicFedoraFunctionality(FedoraTestCase):
    pidspace = FEDORA_PIDSPACE	# will be used for any objects ingested with ingestFixture

    # TODO: test Repository initialization with and without django settings
    
    def test_get_next_pid(self):
        pid = self.repo.get_next_pid()
        self.assertTrue(pid)

        PID_SPACE = 'python-eulcore-test'
        pid = self.repo.get_next_pid(namespace=PID_SPACE)
        self.assertTrue(pid.startswith(PID_SPACE))

        COUNT = 3
        pids = self.repo.get_next_pid(namespace=PID_SPACE, count=COUNT)
        self.assertEqual(len(pids), COUNT)
        for pid in pids:
            self.assertTrue(pid.startswith(PID_SPACE))


    def test_ingest_without_pid(self):
        object = load_fixture_data('basic-object.foxml')
        pid = self.repo.ingest(object)
        self.assertTrue(pid)
        self.repo.purge_object(pid)

        # test ingesting with log message
        pid = self.repo.ingest(object, "this is my test ingest message")
        # ingest message is stored in AUDIT datastream
        # - can currently only be accessed by retrieving entire object xml
        xml, url = self.repo.api.getObjectXML(pid)
        self.assertTrue("this is my test ingest message" in xml)
        purged = self.repo.purge_object(pid, "removing test ingest object")
        self.assertTrue(purged)
        # FIXME: how can we test logMessage arg to purge?
        #  -- have no idea where log message is actually stored... (if anywhere)

    def test_get_object(self):       
        
        testpid = "testpid:1"
        # without info:fedora/ prefix
        obj = self.repo.get_object(testpid)
        self.assertTrue(isinstance(obj, DigitalObject))
        self.assertEqual(obj.pid, testpid)

        # with info:fedora/ prefix
        obj = self.repo.get_object("info:fedora/"+testpid)
        self.assertTrue(isinstance(obj, DigitalObject))
        self.assertEqual(obj.pid, testpid)
        
        class MyDigitalObject(DigitalObject):
            pass

        # specified type
        obj = self.repo.get_object(testpid, MyDigitalObject)
        self.assertTrue(isinstance(obj, MyDigitalObject))
        
        # new object 
        obj = self.repo.get_object()
        self.assertTrue(isinstance(obj, DigitalObject))
        self.assertTrue(obj._create)
        # new object, specified type
        obj = self.repo.get_object(type=MyDigitalObject)
        self.assertTrue(isinstance(obj, MyDigitalObject))
        self.assertTrue(obj._create)



    def test_find_objects(self):
        self.ingestFixture("object-with-pid.foxml")
        pid = self.fedora_fixtures_ingested[0]

        # fielded search
        objects = list(self.repo.find_objects(owner='tester', title='partially-prepared',
                        description='more data'))
        # should find test object
        self.assertEqual(objects[0].pid, pid)
        self.assertEqual(1, len(objects))

        # search by phrase
        objects = list(self.repo.find_objects("more dat? in it than a *"))
        # should find test object
        self.assertEqual(objects[0].pid, pid)

        # ingest 2 more copies of the same test object, then retrieve with chunksize=2
        # - retrieve a second chunk of results with findObjects with a session token
        for p in (1,2):
            self.ingestFixture("object-with-pid.foxml")

        objects = list(self.repo.find_objects(pid="%s:*" % FEDORA_PIDSPACE, chunksize=2))
        # FIXME: this is finding a cmodel object also - leftover from some other test?
        self.assert_(len(objects) >= 3)
        found_pids = [o.pid for o in objects]
        for pid in self.fedora_fixtures_ingested:
            self.assert_(pid in found_pids)

        self.assertRaises(Exception, list, self.repo.find_objects(bogus_field="foo"))

        # django-style field filters
        objects = list(self.repo.find_objects(pid__exact=pid))
        self.assertEqual(objects[0].pid, pid)
        self.assertEqual(1, len(objects))
        objects = list(self.repo.find_objects(created__gt=str(date.today())))
        self.assert_(len(objects) > 0)
        # invalid filter
        self.assertRaises(Exception, list, self.repo.find_objects(created__bogusfilter='foo'))
        

    def test_get_objects_by_cmodel(self):
        self.ingestFixture("object-with-pid.foxml")
        pid = self.fedora_fixtures_ingested[0]
        obj = self.repo.get_object(pid)
        # add a cmodel to test object so we can find our test object by cmodel
        cmodel = DigitalObject(self.api, "control:TestObject")
        obj.add_relationship(modelns.hasModel, cmodel)
        # query by test cmodel
        objs_by_cmodel = self.repo.get_objects_with_cmodel(cmodel.uri)
        self.assertEqual(objs_by_cmodel[0].pid, obj.pid)
        self.assertEqual(len(objs_by_cmodel), 1)

        # query by a non-existent cmodel
        no_cmodel = self.repo.get_objects_with_cmodel("control:NotARealCmodel")
        self.assertEqual([], no_cmodel)
            
    def test_nonssl(self):
        self.ingestFixture('object-with-pid.foxml')
        pid = self.fedora_fixtures_ingested[0]
        repo = Repository(FEDORA_ROOT_NONSSL)
        found = list(repo.find_objects(pid=pid))
        self.assertEqual(1, len(found))

    def test_badhostname(self):
        self.ingestFixture('object-with-pid.foxml')
        pid = self.fedora_fixtures_ingested[0]
        repo = Repository('http://bogus.host.name.foo:8080/fedora/')
        # TODO: currently just a URLError; make test more specific if we add more specific exceptions
        self.assertRaises(Exception, list, repo.find_objects(pid=pid))
        
        # FIXME: is there any way to test that RequestContextManager closes the connection?


     
class TestResourceIndex(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = FEDORA_PIDSPACE
    # relationship predicates for testing
    rel_isMemberOf = "info:fedora/fedora-system:def/relations-external#isMemberOf"
    rel_owner = "info:fedora/fedora-system:def/relations-external#owner"

    def setUp(self):
        super(TestResourceIndex, self).setUp()
        self.risearch = self.repo.risearch
        
        pid = self.fedora_fixtures_ingested[0]
        self.object = self.repo.get_object(pid)
        # add some rels to query
        self.cmodel = DigitalObject(self.api, "control:TestObject")
        self.object.add_relationship(modelns.hasModel, self.cmodel)
        self.related = DigitalObject(self.api, "foo:123")
        self.object.add_relationship(self.rel_isMemberOf, self.related)
        self.object.add_relationship(self.rel_owner, "testuser")

    def testGetPredicates(self):
        # get all predicates for test object
        predicates = list(self.risearch.get_predicates(self.object.uri, None))        
        self.assertTrue(unicode(modelns.hasModel) in predicates)
        self.assertTrue(self.rel_isMemberOf in predicates)
        self.assertTrue(self.rel_owner in predicates)
        # resource
        predicates = list(self.risearch.get_predicates(self.object.uri, self.related.uri))        
        self.assertEqual(predicates[0], self.rel_isMemberOf)
        self.assertEqual(len(predicates), 1)
        # literal
        predicates = list(self.risearch.get_predicates(self.object.uri, "'testuser'"))
        self.assertEqual(predicates[0], self.rel_owner)
        self.assertEqual(len(predicates), 1)

    def testGetSubjects(self):
        subjects = list(self.risearch.get_subjects(self.rel_isMemberOf, self.related.uri))
        self.assertEqual(subjects[0], self.object.uri)
        self.assertEqual(len(subjects), 1)

        # no match
        subjects = list(self.risearch.get_subjects(self.rel_isMemberOf, self.object.uri))
        self.assertEqual(len(subjects), 0)

    def testGetObjects(self):
        objects =  list(self.risearch.get_objects(self.object.uri, modelns.hasModel))
        self.assert_(self.cmodel.uri in objects)
        # also includes generic fedora-object cmodel

    def test_sparql(self):
        # simple sparql to retrieve our test object
        query = '''SELECT ?obj
        WHERE {
            ?obj <%s> "%s"
        }
        ''' % (self.rel_owner, 'testuser')
        objects = list(self.risearch.sparql_query(query))
        self.assert_({'obj': self.object.uri} in objects)

    def test_custom_errors(self):
        self.assertRaises(UnrecognizedQueryLanguage,  self.risearch.find_statements,
                          '* * *', language='bogus')

if __name__ == '__main__':
    main()
