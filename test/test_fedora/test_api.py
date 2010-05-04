#!/usr/bin/env python

from test_fedora.base import FedoraTestCase, load_fixture_data, REPO_ROOT, REPO_ROOT_NONSSL, REPO_USER, REPO_PASS, TEST_PIDSPACE
from eulcore.fedora.api import API_A_LITE, REST_API
from testcore import main
from datetime import date
from time import sleep
import tempfile

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

    def setUp(self):
        super(TestREST_API, self).setUp()
        self.pid = self.fedora_fixtures_ingested[0]
        self.rest_api = REST_API(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)
        self.today = date.today()

    # API-A calls

    # TODO: test findObjects/resumefind

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
        # TODO: possibly add additional datastreams to test object and confirm they are listed
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
        dsid = "TEXT"
        # create a temporary file to upload to Fedora
        
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write(self.TEXT_CONTENT)
        FILE.flush()

        #ssl_rest_api = REST_API(REPO_ROOT, REPO_USER, REPO_PASS)
        #print ssl_rest_api.upload(FILE.name)

        added = self.rest_api.addDatastream(self.pid, dsid, "text datastream",
            mimeType="text/plain", logMessage="creating new datastream",
            controlGroup="M", filename=FILE.name)
        self.assertTrue(added)
        dslist = self.rest_api.listDatastreams(self.pid)
        self.assert_('<datastream dsid="TEXT" label="text datastream" mimeType="text/plain" />'
                in dslist)

        ds_profile = self.rest_api.getDatastream(self.pid, dsid)
        self.assert_('dsID="TEXT" ' in ds_profile)
        self.assert_('<dsLabel>text datastream</dsLabel>' in ds_profile)
        self.assert_('<dsVersionID>TEXT.0</dsVersionID>' in ds_profile)
        self.assert_('<dsCreateDate>%s' % self.today in ds_profile)
        self.assert_('<dsState>A</dsState>' in ds_profile)
        self.assert_('<dsMIME>text/plain</dsMIME>' in ds_profile)
        self.assert_('<dsControlGroup>M</dsControlGroup>' in ds_profile)
        self.assert_('<dsVersionable>true</dsVersionable>' in ds_profile)

        # content returned from fedora should be exactly what we started with
        ds_content = self.rest_api.getDatastreamDissemination(self.pid, dsid)
        self.assertEqual(self.TEXT_CONTENT, ds_content)
        
        # attempt to add to a non-existent object
        added = self.rest_api.addDatastream("bogus:pid", dsid, "text datastream",
            mimeType="text/plain", logMessage="creating new datastream",
            controlGroup="M", filename=FILE.name)
        self.assertFalse(added)

        FILE.close()

    # TODO : test compareDatastreamChecksum

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
        objxml = self.rest_api.getObjectXML(self.pid)
        # TODO/FIXME: update the object so we can look for audit trail in object xml
        self.assert_('<foxml:digitalObject' in objxml)
        self.assert_('<foxml:datastream ID="DC" ' in objxml)

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
        dsid = "TEXT"
        # create a temporary file to upload to Fedora, then modify
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write(self.TEXT_CONTENT)
        FILE.flush()        

        self.rest_api.addDatastream(self.pid, dsid, "text datastream",
            mimeType="text/plain", logMessage="creating new datastream",
            controlGroup="M", filename=FILE.name)
        FILE.close()

        new_text = """Sigh no more, ladies sigh no more.
Men were deceivers ever.
So be you blythe and bonny, singing hey-nonny-nonny."""
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write(new_text)
        FILE.flush()

        # modify managed datastream by file
        updated = self.rest_api.modifyDatastream(self.pid, dsid, "text datastream (modified)",
            mimeType="text/other", logMessage="modifying TEXT datastream", filename=FILE.name)        
        
        self.assertTrue(updated)
        ds_profile = self.rest_api.getDatastream(self.pid, dsid)
        self.assert_('<dsLabel>text datastream (modified)</dsLabel>' in ds_profile)
        self.assert_('<dsVersionID>TEXT.1</dsVersionID>' in ds_profile)
        self.assert_('<dsState>A</dsState>' in ds_profile)
        self.assert_('<dsMIME>text/other</dsMIME>' in ds_profile)  
        
        content = self.rest_api.getDatastreamDissemination(self.pid, "TEXT")
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
        
        profile = self.rest_api.getObjectProfile(self.pid)
        self.assert_('<objLabel>modified test object</objLabel>' in profile)
        self.assert_('<objOwnerId>testuser</objOwnerId>' in profile)
        self.assert_('<objState>I</objState>' in profile)

        modified = self.rest_api.modifyObject("bogus:pid", "modified test object", "testuser",
            "I", "testing modify object")
        self.assertFalse(modified)

    def test_purgeDatastream(self):
        # TODO: check this - attempting to purge a non-existent datastream returns 204?
        #purged = self.rest_api.purgeDatastream(self.pid, "BOGUS",
        #    logMessage="test purging non-existent datastream")

        purged = self.rest_api.purgeDatastream("bogus:pid", "BOGUS",
            logMessage="test purging non-existent datastream from non-existent object")
        self.assertFalse(purged)


        # FIXME/TODO: can't delete DC!  add a new DS and then purge
        #purged = self.rest_api.purgeDatastream(self.pid, "DC", logMessage="purging DC")
        #self.assertTrue(purged)
        
        #dslist = self.rest_api.listDatastreams(self.pid)
        #self.assert_('<datastream dsid="DC"' not in dslist)

        # also TODO: purge specific versions of a datastream

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

        

if __name__ == '__main__':
    main()
