#!/usr/bin/env python

from test_fedora.base import FedoraTestCase, load_fixture_data, REPO_ROOT, REPO_ROOT_NONSSL, REPO_USER, REPO_PASS, TEST_PIDSPACE
from eulcore.fedora.api import REST_API, API_A_LITE, API_M_LITE
from testcore import main
from datetime import date
from time import sleep
import tempfile
import re

# TODO: test for errors - bad pid, dsid, etc


class TestAPI_A_LITE(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestAPI_A_LITE, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.api_a = API_A_LITE(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)

    def testDescribeRepository(self):
        desc = self.api_a.describeRepository()
        self.assert_('<repositoryName>' in desc)
        self.assert_('<repositoryVersion>' in desc)
        self.assert_('<adminEmail>' in desc)

    def testGetDatastreamDissemination(self):
        dc = self.api_a.getDatastreamDissemination(self.pid, "DC")
        self.assert_('<oai_dc:dc' in dc)
        self.assert_('<dc:title>A partially-prepared test object</dc:title>' in dc)
        self.assert_('<dc:description>' in dc)
        self.assert_('<dc:identifier>%s</dc:identifier>' % self.pid in dc)

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
        self.rest_api = REST_API(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)
        self.today = date.today()

    # API-A calls


    def test_findObjects(self):
        found = self.rest_api.findObjects("ownerId~tester")
        print found

        # ingest 2 more copies of the same test object, then retrieve with chunksize=2
        # - retrieve a second chunk of results with findObjects with a session token
        #for p in (1,2):
        #    self.ingestFixture("object-with-pid.foxml")

        #objects = list(self.repo.find_objects(pid="%s:*" % TEST_PIDSPACE, chunksize=2))
        #self.assertEqual(3, len(objects))
        #found_pids = [o.pid for o in objects]
        #for pid in self.fedora_fixtures_ingested:
        #    self.assert_(pid in found_pids)


    def test_getDatastreamDissemination(self):
        dc = self.rest_api.getDatastreamDissemination(self.pid, "DC")
        self.assert_("<dc:title>A partially-prepared test object</dc:title>" in dc)
        self.assert_("<dc:description>This object has more data" in dc)
        self.assert_("<dc:identifier>%s</dc:identifier>" % self.pid in dc)

    #def test_getDissemination(self):
        # testing with built-in fedora dissemination
        # getting 404
        #profile = self.rest_api.getDissemination(self.pid, "fedora-system:3", "viewObjectProfile")

    def test_getObjectHistory(self):
        history = self.rest_api.getObjectHistory(self.pid)
        self.assert_('<fedoraObjectHistory' in history)
        self.assert_('pid="%s"' % self.pid in history)
        self.assert_('<objectChangeDate>%s' % self.today in history)

    def test_getObjectProfile(self):
        profile = self.rest_api.getObjectProfile(self.pid)
        self.assert_('<objectProfile' in profile)
        self.assert_('pid="%s"' % self.pid in profile)
        self.assert_('<objLabel>A partially-prepared test object</objLabel>' in profile)
        self.assert_('<objOwnerId>tester</objOwnerId>' in profile)
        self.assert_('<objCreateDate>%s' % self.today in profile)
        self.assert_('<objLastModDate>%s' % self.today in profile)
        self.assert_('<objState>A</objState>' in profile)
        # unchecked: objDissIndexViewURL, objItemIndexViewURL

    def test_listDatastreams(self):
        dslist = self.rest_api.listDatastreams(self.pid)
        self.assert_('<objectDatastreams' in dslist)
        # TODO: possibly add additional datastreams to test object and confirm they are listed?
        self.assert_('<datastream dsid="DC" label="Dublin Core" mimeType="text/xml"' in dslist)
        
    def test_listMethods(self):
        methods = self.rest_api.listMethods(self.pid)
        self.assert_('<objectMethods' in methods)
        self.assert_('pid="%s"' % self.pid in methods)
        # default fedora methods, should be available on every object
        self.assert_('<sDef pid="fedora-system:3" ' in methods)
        self.assert_('<method name="viewObjectProfile"' in methods)
        self.assert_('<method name="viewItemIndex"' in methods)

        # methods for a specified sdef
        # NOTE: this causes a 404 error; fedora bug? possibly does not work with system methods?
        # methods = self.rest_api.listMethods(self.pid, 'fedora-system:3')

    # API-M calls

    def test_addDatastream(self):
        # returns result from addDatastream call and info used for add
        (added, ds) = self._add_text_datastream()

        self.assertTrue(added)  # response from addDatastream
        self.assert_(ds['logMessage'] in self.rest_api.getObjectXML(self.pid))
        dslist = self.rest_api.listDatastreams(self.pid)
        self.assert_('<datastream dsid="%(id)s" label="%(label)s" mimeType="%(mimeType)s" />'
            % ds  in dslist)
        ds_profile = self.rest_api.getDatastream(self.pid, ds['id'])
        self.assert_('dsID="%s" ' % ds['id'] in ds_profile)
        self.assert_('<dsLabel>%s</dsLabel>' % ds['label'] in ds_profile)
        self.assert_('<dsVersionID>%s.0</dsVersionID>' % ds['id'] in ds_profile)
        self.assert_('<dsCreateDate>%s' % self.today in ds_profile)
        self.assert_('<dsState>A</dsState>' in ds_profile)
        self.assert_('<dsMIME>%s</dsMIME>' % ds['mimeType'] in ds_profile)
        self.assert_('<dsControlGroup>%s</dsControlGroup>' % ds['controlGroup'] in ds_profile)
        self.assert_('<dsVersionable>true</dsVersionable>' in ds_profile)

        # content returned from fedora should be exactly what we started with
        ds_content = self.rest_api.getDatastreamDissemination(self.pid, ds['id'])
        self.assertEqual(self.TEXT_CONTENT, ds_content)
        
        # attempt to add to a non-existent object
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write("bogus")
        FILE.flush()
        added = self.rest_api.addDatastream("bogus:pid", 'TEXT', "text datastream",
            mimeType="text/plain", logMessage="creating new datastream",
            controlGroup="M", filename=FILE.name)
        self.assertFalse(added)

        FILE.close()

    def test_compareDatastreamChecksum(self):
        # create datastream with checksum
        (added, ds) = self._add_text_datastream()        
        ds_info = self.rest_api.compareDatastreamChecksum(self.pid, ds['id'])
        self.assert_('<dsChecksum>bfe1f7b3410d1e86676c4f7af2a84889</dsChecksum>' in ds_info)
        # FIXME: how to test that checksum has actually been checked?

        # check for log message in audit trail
        self.assert_(ds['logMessage'] in self.rest_api.getObjectXML(self.pid))        

    def test_export(self):
        export = self.rest_api.export(self.pid)
        self.assert_('<foxml:datastream' in export)
        self.assert_('PID="%s"' % self.pid in export)
        self.assert_('<foxml:property' in export)
        self.assert_('<foxml:datastream ID="DC" ' in export)

        # default 'context' is public; also test migrate & archive
        # FIXME/TODO: add more datastreams/versions so export formats differ ?

        export = self.rest_api.export(self.pid, context="migrate")
        self.assert_('<foxml:datastream' in export)

        export = self.rest_api.export(self.pid, context="archive")
        self.assert_('<foxml:datastream' in export)

    def test_getDatastream(self):
        ds_profile = self.rest_api.getDatastream(self.pid, "DC")        
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

    # TODO: test getNextPid - but result handling is going to change.. (?)

    def test_getObjectXML(self):
        # update the object so we can look for audit trail in object xml
        (added, ds) = self._add_text_datastream()   
        objxml = self.rest_api.getObjectXML(self.pid)
        self.assert_('<foxml:digitalObject' in objxml)
        self.assert_('<foxml:datastream ID="DC" ' in objxml)
        # audit trail accessible in full xml
        self.assert_('<audit:auditTrail ' in objxml)    

    def test_ingest(self):
        object = load_fixture_data('basic-object.foxml')
        pid = self.rest_api.ingest(object)
        self.assertTrue(pid)
        self.rest_api.purgeObject(pid)

        # test ingesting with log message
        pid = self.rest_api.ingest(object, "this is my test ingest message")
        # ingest message is stored in AUDIT datastream
        # - can currently only be accessed by retrieving entire object xml
        self.assertTrue("this is my test ingest message" in self.rest_api.getObjectXML(pid))
        self.rest_api.purgeObject(pid, "removing test ingest object")

    def test_modifyDatastream(self):
        # add a datastream to be modified
        (added, ds) = self._add_text_datastream()   

        new_text = """Sigh no more, ladies sigh no more.
Men were deceivers ever.
So be you blythe and bonny, singing hey-nonny-nonny."""
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write(new_text)
        FILE.flush()

        # modify managed datastream by file
        updated = self.rest_api.modifyDatastream(self.pid, ds['id'], "text datastream (modified)",
            mimeType="text/other", logMessage="modifying TEXT datastream", filename=FILE.name)                
        self.assertTrue(updated)
        # log message in audit trail
        self.assert_('modifying TEXT datastream' in self.rest_api.getObjectXML(self.pid))

        ds_profile = self.rest_api.getDatastream(self.pid, ds['id'])
        self.assert_('<dsLabel>text datastream (modified)</dsLabel>' in ds_profile)
        self.assert_('<dsVersionID>%s.1</dsVersionID>' % ds['id'] in ds_profile)
        self.assert_('<dsState>A</dsState>' in ds_profile)
        self.assert_('<dsMIME>text/other</dsMIME>' in ds_profile)  
        
        content = self.rest_api.getDatastreamDissemination(self.pid, ds['id'])
        self.assertEqual(content, new_text)       

        # modify DC (inline xml) by string
        new_dc = """<oai_dc:dc
            xmlns:dc='http://purl.org/dc/elements/1.1/'
            xmlns:oai_dc='http://www.openarchives.org/OAI/2.0/oai_dc/'>
          <dc:title>Test-Object</dc:title>
          <dc:description>modified!</dc:description>
        </oai_dc:dc>"""
        updated = self.rest_api.modifyDatastream(self.pid, "DC", "Dublin Core",
            mimeType="text/xml", logMessage="updating DC", content=new_dc)
        self.assertTrue(updated)
        dc = self.rest_api.getDatastreamDissemination(self.pid, "DC")
        # fedora changes whitespace in xml, so exact test fails
        self.assert_('<dc:title>Test-Object</dc:title>' in dc)
        self.assert_('<dc:description>modified!</dc:description>' in dc)

        # bogus pid
        updated = self.rest_api.modifyDatastream("bogus:pid", "TEXT", "Text DS",
            mimeType="text/plain", logMessage="modifiying non-existent DS", filename=FILE.name)
        self.assertFalse(updated)    

        FILE.close()

    def test_modifyObject(self):
        modified = self.rest_api.modifyObject(self.pid, "modified test object", "testuser",
            "I", "testing modify object")
        self.assertTrue(modified)
        # log message in audit trail
        self.assert_('testing modify object' in self.rest_api.getObjectXML(self.pid))
        
        profile = self.rest_api.getObjectProfile(self.pid)
        self.assert_('<objLabel>modified test object</objLabel>' in profile)
        self.assert_('<objOwnerId>testuser</objOwnerId>' in profile)
        self.assert_('<objState>I</objState>' in profile)

        modified = self.rest_api.modifyObject("bogus:pid", "modified test object", "testuser",
            "I", "testing modify object")
        self.assertFalse(modified)

    def test_purgeDatastream(self):
        # add a datastream that can be purged
        (added, ds) = self._add_text_datastream()          

        purged = self.rest_api.purgeDatastream(self.pid, ds['id'], logMessage="purging text datastream")
        self.assertTrue(purged)
        # log message in audit trail
        self.assert_('purging text datastream' in self.rest_api.getObjectXML(self.pid))
        # datastream no longer listed
        dslist = self.rest_api.listDatastreams(self.pid)
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
        ds_profile = self.rest_api.getDatastream(self.pid, "DC")
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
        ds_profile = self.rest_api.getDatastream(self.pid, "DC")
        self.assert_('<dsVersionable>false</dsVersionable>' in ds_profile)

        # bad datastream id
        set_versioned = self.rest_api.setDatastreamVersionable(self.pid, "BOGUS", False)
        self.assertFalse(set_versioned)

        # non-existent pid
        set_versioned = self.rest_api.setDatastreamVersionable("bogus:pid", "DC", True)
        self.assertFalse(set_versioned)


class TestAPI_M_LITE(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestAPI_M_LITE, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.api_m = API_M_LITE(REPO_ROOT, REPO_USER, REPO_PASS)

    def testUpload(self):
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write("Here is some temporary content to upload to fedora.")
        FILE.flush()

        upload_id = self.api_m.upload(FILE.name)
        # current format looks like uploaded://####
        pattern = re.compile('uploaded://[0-9]+')
        self.assert_(pattern.match(upload_id))



if __name__ == '__main__':
    main()
