#!/usr/bin/env python

from test_fedora.base import FedoraTestCase, load_fixture_data, REPO_ROOT_NONSSL, REPO_USER, REPO_PASS, TEST_PIDSPACE
from eulcore.fedora.server import Repository, DigitalObject, ObjectDatastream, URI_HAS_MODEL

from eulcore import xmlmap
import rdflib
from testcore import main

class TestBasicFedoraFunctionality(FedoraTestCase):
    pidspace = TEST_PIDSPACE	# will be used for any objects ingested with ingestFixture
    def testGetNextPID(self):
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


    def testIngestWithoutPid(self):
        object = load_fixture_data('basic-object.foxml')
        pid = self.repo.ingest(object)
        self.assertTrue(pid)
        self.repo.purge_object(pid)

        # test ingesting with log message
        pid = self.repo.ingest(object, "this is my test ingest message")
        # ingest message is stored in AUDIT datastream
        # - can currently only be accessed by retrieving entire object xml
        self.assertTrue("this is my test ingest message" in self.repo.rest_api.getObjectXML(pid))
        self.repo.purge_object(pid, "removing test ingest object")
        # FIXME: how can we test logMessage arg to purge?
        #  -- have no idea where log message is actually stored... (if anywhere)

    def testGetObject(self):
        # get_object doesn't currently check/require that object exists in Fedora...
        
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

    def testFindObjects(self):
        self.ingestFixture("object-with-pid.foxml")
        pid = self.fedora_fixtures_ingested[0]

        objects = list(self.repo.find_objects(ownerId='tester'))
        # should find test object
        self.assertEqual(objects[0].pid, pid)
        # FIXME: is this a reasonable test? do we need a more specific query?
        self.assertEqual(1, len(objects))

        # ingest 2 more copies of the same test object, then retrieve with chunksize=2
        # - retrieve a second chunk of results with findObjects with a session token
        for p in (1,2):
            self.ingestFixture("object-with-pid.foxml")

        objects = list(self.repo.find_objects(pid="%s:*" % TEST_PIDSPACE, chunksize=2))
        self.assertEqual(3, len(objects))
        found_pids = [o.pid for o in objects]
        for pid in self.fedora_fixtures_ingested:
            self.assert_(pid in found_pids)

    def testGetObjectsByCmodel(self):
        self.ingestFixture("object-with-pid.foxml")
        pid = self.fedora_fixtures_ingested[0]
        obj = self.repo.get_object(pid)
        # add a cmodel to test object so we can find our test object by cmodel
        cmodel = DigitalObject("control:TestObject", self.repo.fedora_root)
        obj.add_relationship(URI_HAS_MODEL, cmodel)
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
        repo = Repository(REPO_ROOT_NONSSL)
        found = list(repo.find_objects(pid=pid))
        self.assertEqual(1, len(found))

    def test_badhostname(self):
        self.ingestFixture('object-with-pid.foxml')
        pid = self.fedora_fixtures_ingested[0]
        repo = Repository('http://bogus.host.name.foo:8080/fedora/')
        # TODO: currently just a URLError; make test more specific if we add more specific exceptions
        self.assertRaises(Exception, list, repo.find_objects(pid=pid))
        
        # FIXME: is there any way to test that RequestContextManager closes the connection?


class TestDigitalObject(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestDigitalObject, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.object = self.repo.get_object(self.pid)

    def testBasicProperties(self):
        self.assertEqual(self.pid, self.object.pid)
        self.assertTrue(self.object.uri.startswith("info:fedora/"))
        self.assertTrue(self.object.uri.endswith(self.pid))

    def testGetDatastream(self):
        dc = self.object.get_datastream("DC")
        self.assert_("<dc:title>" in dc)

    def testGetDatastreamAsXml(self):
        class SimpleDC(xmlmap.XmlObject):
            title = xmlmap.StringField('dc:title')
            description = xmlmap.StringField('dc:description')

        dc = self.object.get_datastream_as_xml("DC", SimpleDC)
        self.assertTrue(isinstance(dc, SimpleDC))
        self.assertEqual(dc.title, "A partially-prepared test object")

    def testGetDatastreams(self):
        ds_list = self.object.get_datastreams()        
        self.assert_("DC" in ds_list.keys())
        self.assert_(isinstance(ds_list["DC"], ObjectDatastream))
        dc = ds_list["DC"]
        self.assertEqual("DC", dc.dsid)
        self.assertEqual("Dublin Core", dc.label)
        self.assertEqual("text/xml", dc.mimeType)

    def testRelationships(self):
        # tests add & get rel methods

        # add relation to a resource, by digital object
        related = DigitalObject("foo:123", self.repo.fedora_root)
        isMemberOf = "info:fedora/fedora-system:def/relations-external#isMemberOf"
        added = self.object.add_relationship(isMemberOf, related)
        # FIXME: currently returns None on success (?)      
        rels_ext = self.object.get_datastream("RELS-EXT")        
        self.assert_("isMemberOf" in rels_ext)
        self.assert_(related.uri in rels_ext) # should be full uri, not just pid

        # add relation to a resource, by string
        isMemberOfCollection = "info:fedora/fedora-system:def/relations-external#isMemberOfCollection"
        collection_uri = "info:fedora/foo:456"
        self.object.add_relationship(isMemberOfCollection, collection_uri)
        rels_ext = self.object.get_datastream("RELS-EXT")
        self.assert_("isMemberOfCollection" in rels_ext)
        self.assert_(collection_uri in rels_ext) 

        # add relation to a literal
        self.object.add_relationship("info:fedora/fedora-system:def/relations-external#owner", "testuser")
        rels_ext = self.object.get_datastream("RELS-EXT")
        self.assert_("owner" in rels_ext)
        self.assert_("testuser" in rels_ext)

        rels = self.object.get_relationships()
        self.assert_(isinstance(rels, rdflib.ConjunctiveGraph))
        # convert firxt added relationship to rdflib statement to check that it is in the rdf graph
        st = (rdflib.URIRef(self.object.uri), rdflib.URIRef(isMemberOf), rdflib.URIRef(related.uri))
        self.assertTrue(st in rels)

    #def testGetRelationships(self):
        # TODO: should do something besides HTTPError/404 when object does not have RELS-EXT


    def testHasModel(self):
        cmodel =  DigitalObject("control:ContentType", self.repo.fedora_root)
        # FIXME: currently causes an error because rels-ext datastream does not exist
        #self.assertFalse(self.object.has_model(cmodel.uri))
        self.object.add_relationship(URI_HAS_MODEL, cmodel)
        self.assertTrue(self.object.has_model(cmodel.uri))
        self.assertFalse(self.object.has_model(self.object.uri))

        
class TestResourceIndex(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE
    # relationship predicates for testing
    rel_isMemberOf = "info:fedora/fedora-system:def/relations-external#isMemberOf"
    rel_owner = "info:fedora/fedora-system:def/relations-external#owner"

    def setUp(self):
        super(TestResourceIndex, self).setUp()
        self.risearch = self.repo.risearch

        pid = self.fedora_fixtures_ingested[0]
        self.object = self.repo.get_object(pid)
        # add some rels to query
        self.cmodel = DigitalObject("control:TestObject", self.repo.fedora_root)
        self.object.add_relationship(URI_HAS_MODEL, self.cmodel)
        self.related = DigitalObject("foo:123", self.repo.fedora_root)
        self.object.add_relationship(self.rel_isMemberOf, self.related)
        self.object.add_relationship(self.rel_owner, "testuser")

    def testGetPredicates(self):
        # get all predicates for test object
        predicates = list(self.risearch.get_predicates(self.object.uri, None))        
        self.assertTrue(URI_HAS_MODEL in predicates)
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
        objects =  list(self.risearch.get_objects(self.object.uri, URI_HAS_MODEL))
        self.assert_(self.cmodel.uri in objects)
        # also includes generic fedora-object cmodel

if __name__ == '__main__':
    main()
