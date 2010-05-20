#!/usr/bin/env python

from test_fedora.base import FedoraTestCase, load_fixture_data, REPO_ROOT_NONSSL, REPO_USER, REPO_PASS, TEST_PIDSPACE
from eulcore.fedora.api import REST_API, API_A_LITE, API_M_LITE, API_M
from eulcore.fedora.server import URI_HAS_MODEL
from eulcore.fedora.util import RelativeOpener
from testcore import main
from datetime import date, datetime
from dateutil.tz import tzutc
from time import sleep
import tempfile
import re

# TODO: test for errors - bad pid, dsid, etc

class TestREST_API(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE
    
    TEXT_CONTENT = """This is my text content for a new datastream.
        
Hey, nonny-nonny."""

    def _add_text_datastream(self):        
        # add a text datastream to the current test object - used by multiple tests
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write(self.TEXT_CONTENT)
        FILE.flush()

        # info for calling addDatastream, and return
        ds = {  'id' : 'TEXT', 'label' : 'text datastream', 'mimeType' : 'text/plain',
            'controlGroup' : 'M', 'logMessage' : "creating new datastream",
            'checksumType' : 'MD5'}

        added = self.rest_api.addDatastream(self.pid, ds['id'], ds['label'],
            ds['mimeType'], ds['logMessage'], ds['controlGroup'], filename=FILE.name,
            checksumType=ds['checksumType'])
        FILE.close()
        return (added, ds)

    def setUp(self):
        super(TestREST_API, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.opener = RelativeOpener(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)
        self.rest_api = REST_API(self.opener)
        self.today = date.today()

    # API-A calls

    def test_findObjects(self):
        # search for current test object
        found, url = self.rest_api.findObjects("ownerId~tester")
        self.assert_('<result ' in found)
        self.assert_('<resultList>' in found)
        self.assert_('<pid>%s</pid>' % self.pid in found)

        # crazy search that shouldn't match anything
        found = self.rest_api.findObjects("title~supercalifragilistexpi...")
        self.assert_('<objectFields>' not in found)

        # search for everything - get enough results to get a session token
        # - note that current test fedora includes a number of control objects
        found, url = self.rest_api.findObjects("title~*")
        self.assert_('<listSession>' in found)
        self.assert_('<token>' in found)

        # NOTE: not testing resumeFind here because it would require parsing the xml
        # for the session token - tested at the server/Repository level

    def test_getDatastreamDissemination(self):
        dc, url = self.rest_api.getDatastreamDissemination(self.pid, "DC")
        self.assert_("<dc:title>A partially-prepared test object</dc:title>" in dc)
        self.assert_("<dc:description>This object has more data" in dc)
        self.assert_("<dc:identifier>%s</dc:identifier>" % self.pid in dc)

        # with date-time param
        now_dc, url = self.rest_api.getDatastreamDissemination(self.pid, "DC",
            asOfDateTime=datetime.utcnow())
        self.assertEqual(dc, now_dc)    # should be unchanged
        
        # bogus datastream
        self.assertRaises(Exception, self.rest_api.getDatastreamDissemination,
            self.pid, "BOGUS")

        # bogus pid
        self.assertRaises(Exception, self.rest_api.getDatastreamDissemination,
            "bogus:pid", "BOGUS")

    #def test_getDissemination(self):
        # testing with built-in fedora dissemination
        # getting 404
        #profile = self.rest_api.getDissemination(self.pid, "fedora-system:3", "viewObjectProfile")

    def test_getObjectHistory(self):
        history, url = self.rest_api.getObjectHistory(self.pid)
        self.assert_('<fedoraObjectHistory' in history)
        self.assert_('pid="%s"' % self.pid in history)
        self.assert_('<objectChangeDate>%s' % self.today in history)

        # bogus pid
        self.assertRaises(Exception, self.rest_api.getObjectHistory, "bogus:pid")

    def test_getObjectProfile(self):
        profile, url = self.rest_api.getObjectProfile(self.pid)
        self.assert_('<objectProfile' in profile)
        self.assert_('pid="%s"' % self.pid in profile)
        self.assert_('<objLabel>A partially-prepared test object</objLabel>' in profile)
        self.assert_('<objOwnerId>tester</objOwnerId>' in profile)
        self.assert_('<objCreateDate>%s' % self.today in profile)
        self.assert_('<objLastModDate>%s' % self.today in profile)
        self.assert_('<objState>A</objState>' in profile)
        # unchecked: objDissIndexViewURL, objItemIndexViewURL

        # with time
        profile_now, url = self.rest_api.getObjectProfile(self.pid, asOfDateTime=datetime.utcnow())
        self.assertEqual(profile, profile_now)

        # bogus pid        
        self.assertRaises(Exception, self.rest_api.getObjectHistory, "bogus:pid")

    def test_listDatastreams(self):
        dslist, url = self.rest_api.listDatastreams(self.pid)
        self.assert_('<objectDatastreams' in dslist)        
        self.assert_('<datastream dsid="DC" label="Dublin Core" mimeType="text/xml"' in dslist)

        # bogus pid
        self.assertRaises(Exception, self.rest_api.listDatastreams, "bogus:pid")

        
    def test_listMethods(self):
        methods, url = self.rest_api.listMethods(self.pid)
        self.assert_('<objectMethods' in methods)
        self.assert_('pid="%s"' % self.pid in methods)
        # default fedora methods, should be available on every object
        self.assert_('<sDef pid="fedora-system:3" ' in methods)
        self.assert_('<method name="viewObjectProfile"' in methods)
        self.assert_('<method name="viewItemIndex"' in methods)

        # methods for a specified sdef
        # NOTE: this causes a 404 error; fedora bug? possibly does not work with system methods?
        # methods = self.rest_api.listMethods(self.pid, 'fedora-system:3')

        self.assertRaises(Exception, self.rest_api.listMethods, "bogus:pid")

    # API-M calls

    def test_addDatastream(self):
        # returns result from addDatastream call and info used for add
        ((added, msg), ds) = self._add_text_datastream()

        self.assertTrue(added)  # response from addDatastream
        message, url = self.rest_api.getObjectXML(self.pid)
        self.assert_(ds['logMessage'] in message)
        dslist, url = self.rest_api.listDatastreams(self.pid)
        self.assert_('<datastream dsid="%(id)s" label="%(label)s" mimeType="%(mimeType)s" />'
            % ds  in dslist)
        ds_profile, url = self.rest_api.getDatastream(self.pid, ds['id'])
        self.assert_('dsID="%s" ' % ds['id'] in ds_profile)
        self.assert_('<dsLabel>%s</dsLabel>' % ds['label'] in ds_profile)
        self.assert_('<dsVersionID>%s.0</dsVersionID>' % ds['id'] in ds_profile)
        self.assert_('<dsCreateDate>%s' % self.today in ds_profile)
        self.assert_('<dsState>A</dsState>' in ds_profile)
        self.assert_('<dsMIME>%s</dsMIME>' % ds['mimeType'] in ds_profile)
        self.assert_('<dsControlGroup>%s</dsControlGroup>' % ds['controlGroup'] in ds_profile)
        self.assert_('<dsVersionable>true</dsVersionable>' in ds_profile)

        # content returned from fedora should be exactly what we started with
        ds_content, url = self.rest_api.getDatastreamDissemination(self.pid, ds['id'])
        self.assertEqual(self.TEXT_CONTENT, ds_content)
        
        # attempt to add to a non-existent object
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write("bogus")
        FILE.flush()
        (added, msg) = self.rest_api.addDatastream("bogus:pid", 'TEXT', "text datastream",
            mimeType="text/plain", logMessage="creating new datastream",
            controlGroup="M", filename=FILE.name)
        self.assertFalse(added)
        self.assertEqual("no path in db registry for [bogus:pid]", msg)

        FILE.close()

    def test_compareDatastreamChecksum(self):
        # create datastream with checksum
        (added, ds) = self._add_text_datastream()        
        ds_info, pid = self.rest_api.compareDatastreamChecksum(self.pid, ds['id'])
        self.assert_('<dsChecksum>bfe1f7b3410d1e86676c4f7af2a84889</dsChecksum>' in ds_info)
        # FIXME: how to test that checksum has actually been checked?

        # check for log message in audit trail
        xml, url = self.rest_api.getObjectXML(self.pid)
        self.assert_(ds['logMessage'] in xml)

    def test_export(self):
        export, url = self.rest_api.export(self.pid)
        self.assert_('<foxml:datastream' in export)
        self.assert_('PID="%s"' % self.pid in export)
        self.assert_('<foxml:property' in export)
        self.assert_('<foxml:datastream ID="DC" ' in export)

        # default 'context' is public; also test migrate & archive
        # FIXME/TODO: add more datastreams/versions so export formats differ ?

        export, url = self.rest_api.export(self.pid, context="migrate")
        self.assert_('<foxml:datastream' in export)

        export, url = self.rest_api.export(self.pid, context="archive")
        self.assert_('<foxml:datastream' in export)

        # bogus id
        self.assertRaises(Exception, self.rest_api.export, "bogus:pid")

    def test_getDatastream(self):
        ds_profile, url = self.rest_api.getDatastream(self.pid, "DC")        
        self.assert_('<datastreamProfile' in ds_profile)
        self.assert_('pid="%s"' % self.pid in ds_profile)
        self.assert_('dsID="DC" ' in ds_profile)
        self.assert_('<dsLabel>Dublin Core</dsLabel>' in ds_profile)
        self.assert_('<dsVersionID>DC.0</dsVersionID>' in ds_profile)
        self.assert_('<dsCreateDate>%s' % self.today in ds_profile)
        self.assert_('<dsState>A</dsState>' in ds_profile)
        self.assert_('<dsMIME>text/xml</dsMIME>' in ds_profile)
        self.assert_('<dsControlGroup>X</dsControlGroup>' in ds_profile)
        self.assert_('<dsVersionable>true</dsVersionable>' in ds_profile)

        # with date param
        ds_profile_now, url = self.rest_api.getDatastream(self.pid, "DC", asOfDateTime=datetime.utcnow())
        self.assertEqual(ds_profile, ds_profile_now)
        
        # bogus datastream id on valid pid
        self.assertRaises(Exception, self.rest_api.getDatastream, self.pid, "BOGUS")

        # bogus pid
        self.assertRaises(Exception, self.rest_api.getDatastream, "bogus:pid", "DC")
        
    def test_getNextPID(self):
        pids, url = self.rest_api.getNextPID()
        self.assert_('<pidList' in pids)
        self.assert_('<pid>' in pids)

        pids, url = self.rest_api.getNextPID(numPIDs=3, namespace="test-ns")        
        self.assertEqual(3, pids.count("<pid>test-ns:"))        

    def test_getObjectXML(self):
        # update the object so we can look for audit trail in object xml
        added, ds = self._add_text_datastream()   
        objxml, url = self.rest_api.getObjectXML(self.pid)
        self.assert_('<foxml:digitalObject' in objxml)
        self.assert_('<foxml:datastream ID="DC" ' in objxml)
        # audit trail accessible in full xml
        self.assert_('<audit:auditTrail ' in objxml)

        # bogus id
        self.assertRaises(Exception, self.rest_api.getObjectXML, "bogus:pid")

    def test_ingest(self):
        object = load_fixture_data('basic-object.foxml')
        pid = self.rest_api.ingest(object)
        self.assertTrue(pid)
        self.rest_api.purgeObject(pid)

        # test ingesting with log message
        pid = self.rest_api.ingest(object, "this is my test ingest message")
        # ingest message is stored in AUDIT datastream
        # - can currently only be accessed by retrieving entire object xml
        xml, url = self.rest_api.getObjectXML(pid)
        self.assertTrue("this is my test ingest message" in xml)
        self.rest_api.purgeObject(pid, "removing test ingest object")

    def test_modifyDatastream(self):
        # add a datastream to be modified
        added, ds = self._add_text_datastream()   

        new_text = """Sigh no more, ladies sigh no more.
Men were deceivers ever.
So be you blythe and bonny, singing hey-nonny-nonny."""
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write(new_text)
        FILE.flush()

        # modify managed datastream by file
        updated, msg = self.rest_api.modifyDatastream(self.pid, ds['id'], "text datastream (modified)",
            mimeType="text/other", logMessage="modifying TEXT datastream", filename=FILE.name)                
        self.assertTrue(updated)
        # log message in audit trail
        xml, url = self.rest_api.getObjectXML(self.pid)
        self.assert_('modifying TEXT datastream' in xml)

        ds_profile, url = self.rest_api.getDatastream(self.pid, ds['id'])
        self.assert_('<dsLabel>text datastream (modified)</dsLabel>' in ds_profile)
        self.assert_('<dsVersionID>%s.1</dsVersionID>' % ds['id'] in ds_profile)
        self.assert_('<dsState>A</dsState>' in ds_profile)
        self.assert_('<dsMIME>text/other</dsMIME>' in ds_profile)  
        
        content, url = self.rest_api.getDatastreamDissemination(self.pid, ds['id'])
        self.assertEqual(content, new_text)       

        # modify DC (inline xml) by string
        new_dc = """<oai_dc:dc
            xmlns:dc='http://purl.org/dc/elements/1.1/'
            xmlns:oai_dc='http://www.openarchives.org/OAI/2.0/oai_dc/'>
          <dc:title>Test-Object</dc:title>
          <dc:description>modified!</dc:description>
        </oai_dc:dc>"""
        updated, msg = self.rest_api.modifyDatastream(self.pid, "DC", "Dublin Core",
            mimeType="text/xml", logMessage="updating DC", content=new_dc)
        self.assertTrue(updated)
        dc, url = self.rest_api.getDatastreamDissemination(self.pid, "DC")
        # fedora changes whitespace in xml, so exact test fails
        self.assert_('<dc:title>Test-Object</dc:title>' in dc)
        self.assert_('<dc:description>modified!</dc:description>' in dc)

        # bogus datastream on valid pid
        updated, msg = self.rest_api.modifyDatastream(self.pid, "BOGUS", "Text DS",
            mimeType="text/plain", logMessage="modifiying non-existent DS", filename=FILE.name)
        self.assertFalse(updated)
        # NOTE: error message is useless in this case (java null pointer)  - fedora bug

        # bogus pid
        updated, msg = self.rest_api.modifyDatastream("bogus:pid", "TEXT", "Text DS",
            mimeType="text/plain", logMessage="modifiying non-existent DS", filename=FILE.name)
        self.assertFalse(updated)
        self.assertEqual("no path in db registry for [bogus:pid]", msg)

        FILE.close()

    def test_modifyObject(self):
        modified = self.rest_api.modifyObject(self.pid, "modified test object", "testuser",
            "I", "testing modify object")
        self.assertTrue(modified)
        # log message in audit trail
        xml, url = self.rest_api.getObjectXML(self.pid)
        self.assert_('testing modify object' in xml)
        
        profile, xml = self.rest_api.getObjectProfile(self.pid)
        self.assert_('<objLabel>modified test object</objLabel>' in profile)
        self.assert_('<objOwnerId>testuser</objOwnerId>' in profile)
        self.assert_('<objState>I</objState>' in profile)

        # bogus id
        modified = self.rest_api.modifyObject("bogus:pid", "modified test object", "testuser",
            "I", "testing modify object")
        self.assertFalse(modified)

    def test_purgeDatastream(self):
        # add a datastream that can be purged
        added, ds = self._add_text_datastream()          

        purged = self.rest_api.purgeDatastream(self.pid, ds['id'], logMessage="purging text datastream")
        self.assertTrue(purged)
        # log message in audit trail
        xml, url = self.rest_api.getObjectXML(self.pid)
        self.assert_('purging text datastream' in xml)
        # datastream no longer listed
        dslist, url = self.rest_api.listDatastreams(self.pid)
        self.assert_('<datastream dsid="%s"' % ds['id'] not in dslist)

        # NOTE: Fedora bug - attempting to purge a non-existent datastream returns 204?
        #purged = self.rest_api.purgeDatastream(self.pid, "BOGUS",
        #    logMessage="test purging non-existent datastream")
        #self.assertFalse(purged)

        purged = self.rest_api.purgeDatastream("bogus:pid", "BOGUS",
            logMessage="test purging non-existent datastream from non-existent object")
        self.assertFalse(purged)   
        
        # also test purging specific versions of a datastream ? 

    def test_purgeObject(self):
        object = load_fixture_data('basic-object.foxml')
        pid = self.rest_api.ingest(object)        
        purged = self.rest_api.purgeObject(pid)
        self.assertTrue(purged)

        # NOTE: fedora doesn't notice the object has been purged right away
        sleep(7)    # 5-6 was fastest this worked; padding to avoid spurious failures
        self.assertRaises(Exception, self.rest_api.getObjectProfile, pid)

        # bad pid
        purged = self.rest_api.purgeObject("bogus:pid")
        self.assertFalse(purged)

    def test_setDatastreamState(self):
        set_state = self.rest_api.setDatastreamState(self.pid, "DC", "I")
        self.assertTrue(set_state)

        # get datastream to confirm change
        ds_profile, url = self.rest_api.getDatastream(self.pid, "DC")
        self.assert_('<dsState>I</dsState>' in ds_profile)

        # bad datastream id
        set_state = self.rest_api.setDatastreamState(self.pid, "BOGUS", "I")
        self.assertFalse(set_state)

        # non-existent pid
        set_state = self.rest_api.setDatastreamState("bogus:pid", "DC", "D")
        self.assertFalse(set_state)

    def test_setDatastreamVersionable(self):
        set_versioned = self.rest_api.setDatastreamVersionable(self.pid, "DC", False)
        self.assertTrue(set_versioned)

        # get datastream profile to confirm change
        ds_profile, url = self.rest_api.getDatastream(self.pid, "DC")
        self.assert_('<dsVersionable>false</dsVersionable>' in ds_profile)

        # bad datastream id
        set_versioned = self.rest_api.setDatastreamVersionable(self.pid, "BOGUS", False)
        self.assertFalse(set_versioned)

        # non-existent pid
        set_versioned = self.rest_api.setDatastreamVersionable("bogus:pid", "DC", True)
        self.assertFalse(set_versioned)


class TestAPI_A_LITE(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestAPI_A_LITE, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.opener = RelativeOpener(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)
        self.api_a = API_A_LITE(self.opener)

    def testDescribeRepository(self):
        desc, url = self.api_a.describeRepository()
        self.assert_('<repositoryName>' in desc)
        self.assert_('<repositoryVersion>' in desc)
        self.assert_('<adminEmail>' in desc)

    def testGetDatastreamDissemination(self):
        dc, url = self.api_a.getDatastreamDissemination(self.pid, "DC")
        self.assert_('<oai_dc:dc' in dc)
        self.assert_('<dc:title>A partially-prepared test object</dc:title>' in dc)
        self.assert_('<dc:description>' in dc)
        self.assert_('<dc:identifier>%s</dc:identifier>' % self.pid in dc)


class TestAPI_M_LITE(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestAPI_M_LITE, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.api_m = API_M_LITE(self.opener)

    def testUploadString(self):
        data = "Here is some temporary content to upload to fedora."
        upload_id = self.api_m.upload(data)
        # current format looks like uploaded://####
        pattern = re.compile('uploaded://[0-9]+')
        self.assert_(pattern.match(upload_id))

    def testUploadFile(self):
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write("Here is some temporary content to upload to fedora.")
        FILE.flush()

        with open(FILE.name, 'rb') as f:
            upload_id = self.api_m.upload(f)
        # current format looks like uploaded://####
        pattern = re.compile('uploaded://[0-9]+')
        self.assert_(pattern.match(upload_id))


# NOTE: to debug soap, uncomment these lines
#from soaplib.client import debug
#debug(True)

class TestAPI_M(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    # relationship predicates for testing
    rel_isMemberOf = "info:fedora/fedora-system:def/relations-external#isMemberOf"
    rel_owner = "info:fedora/fedora-system:def/relations-external#owner"

    # save date-time before fixtures are created in fedora
    # getting time here instead of setUp should give a little more leeway if server times are not synced
    now = datetime.now(tzutc())   

    def setUp(self):
        super(TestAPI_M, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.api_m = API_M(self.opener)
        self.opener = RelativeOpener(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)
        self.rest_api = REST_API(self.opener)
        
    def test_addRelationship(self):
        # rel to resource
        added = self.api_m.addRelationship(self.pid, URI_HAS_MODEL, "info:fedora/pid:123", False)
        self.assertTrue(added)
        rels, url = self.rest_api.getDatastreamDissemination(self.pid, "RELS-EXT")
        self.assert_('<hasModel' in rels)
        self.assert_('rdf:resource="info:fedora/pid:123"' in rels)

        # literal
        added = self.api_m.addRelationship(self.pid, self.rel_owner, "johndoe", True)
        self.assertTrue(added)
        rels, url = self.rest_api.getDatastreamDissemination(self.pid, "RELS-EXT")
        self.assert_('<owner' in rels)
        self.assert_('>johndoe<' in rels)

        # bogus pid
        self.assertRaises(Exception, self.api_m.addRelationship,
            "bogus:pid", self.rel_owner, "johndoe", True)

    def test_getRelationships(self):
        # add relations
        self.api_m.addRelationship(self.pid, URI_HAS_MODEL, "info:fedora/pid:123", False)
        self.api_m.addRelationship(self.pid, self.rel_owner, "johndoe", True)

        response = self.api_m.getRelationships(self.pid, URI_HAS_MODEL)
        rels = response.relationships

        self.assertEqual(2, len(rels))  # includes fedora-system cmodel
        self.assertEqual(rels[0].subject, 'info:fedora/' + self.pid)
        self.assertEqual(rels[0].predicate, URI_HAS_MODEL)
        cmodels = [rels[0].object, rels[1].object]
        self.assert_('info:fedora/fedora-system:FedoraObject-3.0' in cmodels)
        self.assert_('info:fedora/pid:123' in cmodels)

        response = self.api_m.getRelationships(self.pid, self.rel_owner)
        rels = response.relationships
        self.assertEqual(1, len(rels))
        self.assertEqual(rels[0].subject, 'info:fedora/' + self.pid)
        self.assertEqual(rels[0].predicate, self.rel_owner)
        self.assertEqual(rels[0].object, "johndoe")

    def test_purgeRelationship(self):
        # add relation to purge
        self.api_m.addRelationship(self.pid, URI_HAS_MODEL, "info:fedora/pid:123", False)
        
        purged = self.api_m.purgeRelationship(self.pid, URI_HAS_MODEL, "info:fedora/pid:123", False)
        self.assertEqual(purged, True)

        # purge non-existent rel on valid pid
        purged = self.api_m.purgeRelationship(self.pid, self.rel_owner, "johndoe", True)
        self.assertFalse(purged)

        # bogus pid
        self.assertRaises(Exception, self.api_m.purgeRelationship, "bogus:pid",
            self.rel_owner, "johndoe", True)        

    def test_getDatastreamHistory(self):
        history = self.api_m.getDatastreamHistory(self.pid, "DC")
        self.assertEqual(1, len(history.datastreams))
        dc_info = history.datastreams[0]
        self.assertEqual('X', dc_info.controlGroup)
        self.assertEqual('DC', dc_info.ID)
        self.assertEqual('DC.0', dc_info.versionID)
         # altIDs unused
        self.assertEqual('Dublin Core', dc_info.label)
        self.assertTrue(dc_info.versionable)
        self.assertEqual("text/xml", dc_info.MIMEType)
        # formatURI not set in test fixture
        self.assert_(self.now < dc_info.createDate)     # created after 'now' in setup
        self.assertEqual(490, dc_info.size)     # NOTE: based on current fixture size; is this a useful test?
        self.assertEqual('A', dc_info.state) 
        # location, checksumType, and checksum not set in current fixture
        
        # modify DC so there are multiple versions        
        new_dc = """<oai_dc:dc
            xmlns:dc='http://purl.org/dc/elements/1.1/'
            xmlns:oai_dc='http://www.openarchives.org/OAI/2.0/oai_dc/'>
          <dc:title>Test-Object</dc:title>
          <dc:description>modified!</dc:description>
        </oai_dc:dc>"""
        self.rest_api.modifyDatastream(self.pid, "DC", "DCv2Dublin Core",
            mimeType="text/xml", logMessage="updating DC", content=new_dc)
        history = self.api_m.getDatastreamHistory(self.pid, "DC")
        self.assertEqual(2, len(history.datastreams))
        self.assertEqual('DC.1', history.datastreams[0].versionID)      # newest version is first
        self.assertNotEqual(history.datastreams[0].createDate, history.datastreams[1].createDate)

        # bogus datastream
        self.assertEqual(None, self.api_m.getDatastreamHistory(self.pid, "BOGUS"))

        # bogus pid
        self.assertRaises(Exception, self.api_m.getDatastreamHistory, "bogus:pid", "DC")

if __name__ == '__main__':
    main()
