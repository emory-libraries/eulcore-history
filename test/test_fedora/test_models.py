#!/usr/bin/env python
from datetime import date
from rdflib.Graph import Graph as RdfGraph
import rdflib
import tempfile

from eulcore.fedora.api import ApiFacade
from eulcore.fedora.models import Datastream, DatastreamObject, DigitalObject, \
        XmlDatastream, XmlDatastreamObject, RdfDatastream, RdfDatastreamObject
from eulcore.fedora.server import URI_HAS_MODEL
from eulcore.fedora.util import RelativeOpener
from eulcore.fedora.xml import ObjectDatastream
from eulcore.xmlmap.dc import DublinCore

from test_fedora.base import FedoraTestCase, TEST_PIDSPACE, REPO_ROOT, REPO_USER, REPO_PASS
from testcore import main

class MyDigitalObject(DigitalObject):
    # extend digital object with datastreams for testing
    dc = XmlDatastream("DC", "Dublin Core", DublinCore, defaults={
            'control_group': 'X',
            'format': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        })
    text = Datastream("TEXT", "Text datastream", defaults={
            'mimetype': 'text/plain',
        })
    rels_ext = RdfDatastream("RELS-EXT", "External Relations", defaults={
            'control_group': 'X',
            'format': 'info:fedora/fedora-system:FedoraRELSExt-1.0',
        })

def _add_text_datastream(obj):
    TEXT_CONTENT = "Here is some text content for a non-xml datastream."
    # add a text datastream to the current test object
    FILE = tempfile.NamedTemporaryFile(mode="w", suffix=".txt")
    FILE.write(TEXT_CONTENT)
    FILE.flush()
    # info for calling addDatastream, and return
    ds = {  'id' : 'TEXT', 'label' : 'text datastream', 'mimeType' : 'text/plain',
        'controlGroup' : 'M', 'logMessage' : "creating new datastream", 'versionable': False,
        'checksumType' : 'MD5'}
    obj.api.addDatastream(obj.pid, ds['id'], ds['label'],
        ds['mimeType'], ds['logMessage'], ds['controlGroup'], filename=FILE.name,
        checksumType=ds['checksumType'])
    FILE.close()


class TestDatastreams(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE
    
    TEXT_CONTENT = "Here is some text content for a non-xml datastream."

    def setUp(self):
        super(TestDatastreams, self).setUp()
        self.pid = self.fedora_fixtures_ingested[-1] # get the pid for the last object
        self.obj = MyDigitalObject(self.api, self.pid)

        # add a text datastream to the current test object
        _add_text_datastream(self.obj)

        self.today = str(date.today())

    def test_get_ds_content(self):
        dc = self.obj.dc.content
        self.assert_(isinstance(self.obj.dc, XmlDatastreamObject))
        self.assert_(isinstance(dc, DublinCore))
        self.assertEqual(dc.title, "A partially-prepared test object")
        self.assertEqual(dc.identifier, self.pid)

        self.assert_(isinstance(self.obj.text, DatastreamObject))
        self.assertEqual(self.obj.text.content, self.TEXT_CONTENT)

    def test_get_ds_info(self):
        self.assertEqual(self.obj.dc.label, "Dublin Core")
        self.assertEqual(self.obj.dc.mimetype, "text/xml")
        self.assertEqual(self.obj.dc.state, "A")
        self.assertEqual(self.obj.dc.versionable, True) 
        self.assertEqual(self.obj.dc.control_group, "X")
        self.assert_(self.obj.dc.created.startswith(self.today))

        self.assertEqual(self.obj.text.label, "text datastream")
        self.assertEqual(self.obj.text.mimetype, "text/plain")
        self.assertEqual(self.obj.text.state, "A")
        self.assertEqual(self.obj.text.versionable, True)
        self.assertEqual(self.obj.text.control_group, "M")
        self.assert_(self.obj.text.created.startswith(self.today))

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

    def test_ds_isModified(self):
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

    def test_rdf_datastream(self):
        # add a relationship to test RELS-EXT/rdf datastreams        
        isMemberOf = "info:fedora/fedora-system:def/relations-external#isMemberOf"
        self.obj.add_relationship(isMemberOf, "info:fedora/foo:123")
        
        self.assert_(isinstance(self.obj.rels_ext, RdfDatastreamObject))
        self.assert_(isinstance(self.obj.rels_ext.content, RdfGraph))
        self.assert_("isMemberOf" in self.obj.rels_ext.content.serialize())
        

class TestNewObject(FedoraTestCase):
    pidspace = TEST_PIDSPACE

    def test_basic_ingest(self):
        obj = MyDigitalObject(self.api, pid=self.getNextPid)
        obj.save()

        self.assertTrue(isinstance(obj.pid, basestring))
        self.append_test_pid(obj.pid)
        self.assertTrue(obj.pid.startswith(self.pidspace))

        fetched = MyDigitalObject(self.api, obj.pid)
        self.assertEqual(fetched.dc.content.identifier, obj.pid)

    def test_profile(self):
        obj = MyDigitalObject(self.api, pid=self.getNextPid)
        obj.label = 'test label'
        obj.owner = 'tester'
        obj.state = 'I'
        obj.save()
        self.append_test_pid(obj.pid)

        self.assertEqual(obj.label, 'test label')
        self.assertEqual(obj.owner, 'tester')
        self.assertEqual(obj.state, 'I')

        fetched = MyDigitalObject(self.api, obj.pid)
        self.assertEqual(fetched.label, 'test label')
        self.assertEqual(fetched.owner, 'tester')
        self.assertEqual(fetched.state, 'I')

    def test_default_datastreams(self):
        obj = MyDigitalObject(self.api, pid=self.getNextPid)
        obj.save()
        self.append_test_pid(obj.pid)

        fetched = MyDigitalObject(self.api, obj.pid)

        self.assertEqual(fetched.dc.label, 'Dublin Core')
        self.assertEqual(fetched.dc.mimetype, 'text/xml')
        self.assertEqual(fetched.dc.versionable, False)
        self.assertEqual(fetched.dc.state, 'A')
        self.assertEqual(fetched.dc.format, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        self.assertEqual(fetched.dc.control_group, 'X')
        self.assertEqual(fetched.dc.content.identifier, fetched.pid)

        # skip text for now: it's meaningless unless we give it content

        self.assertEqual(fetched.rels_ext.label, 'External Relations')
        self.assertEqual(fetched.rels_ext.mimetype, 'application/rdf+xml')
        self.assertEqual(fetched.rels_ext.versionable, False)
        self.assertEqual(fetched.rels_ext.state, 'A')
        self.assertEqual(fetched.rels_ext.format, 'info:fedora/fedora-system:FedoraRELSExt-1.0')
        self.assertEqual(fetched.rels_ext.control_group, 'X')
        


class TestDigitalObject(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    def setUp(self):
        super(TestDigitalObject, self).setUp()
        self.pid = self.fedora_fixtures_ingested[-1] # get the pid for the last object
        self.obj = MyDigitalObject(self.api, self.pid)
        _add_text_datastream(self.obj)
        self.today = str(date.today())

    def test_properties(self):
        self.assertEqual(self.pid, self.obj.pid)
        self.assertTrue(self.obj.uri.startswith("info:fedora/"))
        self.assertTrue(self.obj.uri.endswith(self.pid))

    def test_get_object_info(self):
        self.assertEqual(self.obj.label, "A partially-prepared test object")
        self.assertEqual(self.obj.owner, "tester")
        self.assertEqual(self.obj.state, "A")
        self.assert_(self.obj.created.startswith(self.today))
        self.assert_(self.obj.modified.startswith(self.today))

    def test_save_object_info(self):
        self.obj.label = "An updated test object"
        self.obj.owner = "notme"
        self.obj.state = "I"
        saved = self.obj.saveProfile("saving test object profile")
        self.assertTrue(saved, "DigitalObject saveProfile should return True on successful update")
        profile = self.obj.getProfile() # get fresh from fedora to confirm updated
        self.assertEqual(profile.label, "An updated test object")
        self.assertEqual(profile.owner, "notme")
        self.assertEqual(profile.state, "I")
        self.assertNotEqual(profile.created, profile.modified,
                "object create date should not equal modified after updating object profile")

    def test_save(self):
        # unmodified object - save should do nothing
        self.obj.save()

        # modify object profile, datastream content, datastream info
        self.obj.label = "new label"        
        self.obj.dc.content.title = "new dublin core title"
        self.obj.text.label = "text content"
        self.obj.save()

        # confirm all changes were saved to fedora
        profile = self.obj.getProfile() 
        self.assertEqual(profile.label, "new label")
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.dc.id)
        self.assert_('<dc:title>new dublin core title</dc:title>' in data)
        text_info = self.obj.getDatastreamProfile(self.obj.text.id)
        self.assertEqual(text_info.label, "text content")

        # TODO: how to simulate errors saving?
        self.obj.dc.content = "this is not dublin core!"    # NOTE: setting xml content like this could change...
        self.assertRaises(Exception, self.obj.save)

    def test_get_datastreams(self):
        ds_list = self.obj.get_datastreams()
        self.assert_("DC" in ds_list.keys())
        self.assert_(isinstance(ds_list["DC"], ObjectDatastream))
        dc = ds_list["DC"]
        self.assertEqual("DC", dc.dsid)
        self.assertEqual("Dublin Core", dc.label)
        self.assertEqual("text/xml", dc.mimeType)

        self.assert_("TEXT" in ds_list.keys())
        text = ds_list["TEXT"]
        self.assertEqual("text datastream", text.label)
        self.assertEqual("text/plain", text.mimeType)

    def test_has_model(self):
        cmodel_uri = "info:fedora/control:ContentType"
        # FIXME: checking when rels-ext datastream does not exist causes an error
        self.assertFalse(self.obj.has_model(cmodel_uri))
        self.obj.add_relationship(URI_HAS_MODEL, cmodel_uri)
        self.assertTrue(self.obj.has_model(cmodel_uri))
        self.assertFalse(self.obj.has_model(self.obj.uri))

    def test_add_relationships(self):
        # add relation to a resource, by digital object
        related = DigitalObject(self.api, "foo:123")
        isMemberOf = "info:fedora/fedora-system:def/relations-external#isMemberOf"
        added = self.obj.add_relationship(isMemberOf, related)
        self.assertTrue(added, "add relationship should return True on success, got %s" % added)
        rels_ext, url = self.obj.api.getDatastreamDissemination(self.pid, "RELS-EXT")
        self.assert_("isMemberOf" in rels_ext)
        self.assert_(related.uri in rels_ext) # should be full uri, not just pid

        # add relation to a resource, by string
        isMemberOfCollection = "info:fedora/fedora-system:def/relations-external#isMemberOfCollection"
        collection_uri = "info:fedora/foo:456"
        self.obj.add_relationship(isMemberOfCollection, collection_uri)
        rels_ext, url = self.obj.api.getDatastreamDissemination(self.pid, "RELS-EXT")
        self.assert_("isMemberOfCollection" in rels_ext)
        self.assert_(collection_uri in rels_ext)

        # add relation to a literal
        self.obj.add_relationship("info:fedora/fedora-system:def/relations-external#owner", "testuser")
        rels_ext, url = self.obj.api.getDatastreamDissemination(self.pid, "RELS-EXT")
        self.assert_("owner" in rels_ext)
        self.assert_("testuser" in rels_ext)

        rels = self.obj.rels_ext.content
        # convert first added relationship to rdflib statement to check that it is in the rdf graph
        st = (rdflib.URIRef(self.obj.uri), rdflib.URIRef(isMemberOf), rdflib.URIRef(related.uri))
        self.assertTrue(st in rels)

    #def testGetRelationships(self):
        # TODO: should do something besides HTTPError/404 when object does not have RELS-EXT


if __name__ == '__main__':
    main()
