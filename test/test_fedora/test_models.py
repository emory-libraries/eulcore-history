#!/usr/bin/env python
import tempfile

from eulcore.fedora.api import ApiFacade
from eulcore.fedora.util import RelativeOpener
from eulcore.fedora.models import Datastream, DatastreamObject, DigitalObject
from eulcore.xmlmap.dc import DublinCore

from test_fedora.base import FedoraTestCase, TEST_PIDSPACE, REPO_ROOT_NONSSL, REPO_USER, REPO_PASS
from testcore import main

class TestDigitalObject(DigitalObject):
    dc = Datastream("DC", "Dublin Core metadata", DublinCore)
    text = Datastream("TEXT", "Text datastream", defaults={'mimetype': 'text/plain'})

class TestDatastreams(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE
    
    TEXT_CONTENT = "Here is some text content for a non-xml datastream."

    def setUp(self):
        super(TestDatastreams, self).setUp()
        self.pid = self.fedora_fixtures_ingested[-1] # get the pid for the last object
        self.obj = TestDigitalObject()
        self.opener = RelativeOpener(REPO_ROOT_NONSSL, REPO_USER, REPO_PASS)
        self.obj.api = ApiFacade(self.opener)
        self.obj.pid = self.pid

        # add a text datastream to the current test object
        FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
        FILE.write(self.TEXT_CONTENT)
        FILE.flush()
        # info for calling addDatastream, and return
        ds = {  'id' : 'TEXT', 'label' : 'text datastream', 'mimeType' : 'text/plain',
            'controlGroup' : 'M', 'logMessage' : "creating new datastream", 'versionable': False,
            'checksumType' : 'MD5'}
        self.obj.api.addDatastream(self.pid, ds['id'], ds['label'],
            ds['mimeType'], ds['logMessage'], ds['controlGroup'], filename=FILE.name,
            checksumType=ds['checksumType'])
        FILE.close()

    def test_get_content(self):
        dc = self.obj.dc.content
        self.assert_(isinstance(self.obj.dc, DatastreamObject))
        self.assert_(isinstance(dc, DublinCore))
        self.assertEqual(dc.title, "A partially-prepared test object")
        self.assertEqual(dc.identifier, self.pid)

        self.assert_(isinstance(self.obj.text, DatastreamObject))
        self.assertEqual(self.obj.text.content, self.TEXT_CONTENT)

    def test_get_info(self):
        self.assertEqual(self.obj.dc.label, "Dublin Core")
        self.assertEqual(self.obj.dc.mimetype, "text/xml")
        self.assertEqual(self.obj.dc.state, "A")
        self.assertEqual(self.obj.dc.versionable, True) 
        self.assertEqual(self.obj.dc.control_group, "X")

        self.assertEqual(self.obj.text.label, "text datastream")
        self.assertEqual(self.obj.text.mimetype, "text/plain")
        self.assertEqual(self.obj.text.state, "A")
        self.assertEqual(self.obj.text.versionable, True)
        self.assertEqual(self.obj.text.control_group, "M")

    def test_savedatastream(self):
        new_text = "Here is some totally new text content."
        self.obj.text.content = new_text
        self.obj.text.label = "new ds label"
        self.obj.text.mimetype = "text/other"
        self.obj.text.versionable = False
        self.obj.text.state = "I"
        self.obj.text.format = "some.format.uri"
        saved = self.obj.text.save("changed text")
        self.assertTrue(saved, "saving TEXT datastream should return true")
        self.assertEqual(self.obj.text.content, new_text)
        # compare with the datastream pulled directly from Fedora
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.text.id)
        self.assertEqual(data, new_text)
        dsinfo, url = self.obj.api.getDatastream(self.pid, self.obj.text.id)
        self.assert_("<dsLabel>new ds label</dsLabel>" in dsinfo)
        self.assert_("<dsMIME>text/other</dsMIME>" in dsinfo)
        self.assert_("<dsVersionable>false</dsVersionable>" in dsinfo)
        self.assert_("<dsState>I</dsState>" in dsinfo)
        self.assert_("<dsFormatURI>some.format.uri</dsFormatURI>" in dsinfo)
        # look for log message ?

        self.obj.dc.content.title = "this is a new title"
        saved = self.obj.dc.save("changed DC title")
        self.assertTrue(saved, "saving DC datastream should return true")
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.dc.id)
        self.assert_("<dc:title>this is a new title</dc:title>" in data)

    def test_isModified(self):
        self.assertFalse(self.obj.text.isModified(), "isModified should return False for unchanged DC datastream")
        self.assertFalse(self.obj.dc.isModified(), "isModified should return False for unchanged DC datastream")

        self.obj.text.label = "next text label"
        self.assertTrue(self.obj.text.isModified(), "isModified should return True when text datastream label has been updated")

        self.obj.dc.content.description = "new datastream contents"
        self.assertTrue(self.obj.dc.isModified(), "isModified should return True when DC datastream content has changed")

        self.obj.text.save()
        self.obj.dc.save()
        self.assertFalse(self.obj.text.isModified(), "isModified should return False after text datastream has been saved")
        self.assertFalse(self.obj.dc.isModified(), "isModified should return False after DC datastream has been saved")

if __name__ == '__main__':
    main()
