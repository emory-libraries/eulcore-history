#!/usr/bin/env python
from datetime import datetime
from dateutil.tz import tzutc
from rdflib.Graph import Graph as RdfGraph
import rdflib
import tempfile

from eulcore.fedora.models import Datastream, DatastreamObject, DigitalObject, \
        XmlDatastream, XmlDatastreamObject, RdfDatastream, RdfDatastreamObject, \
        DigitalObjectSaveFailure
from eulcore.fedora.server import URI_HAS_MODEL
from eulcore.fedora.xml import ObjectDatastream
from eulcore.xmlmap.dc import DublinCore

from test_fedora.base import FedoraTestCase, TEST_PIDSPACE
from testcore import main

class MyDigitalObject(DigitalObject):
    # extend digital object with datastreams for testing
    dc = XmlDatastream("DC", "Dublin Core", DublinCore, defaults={
            'control_group': 'X',
            'format': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        })
    rels_ext = RdfDatastream("RELS-EXT", "External Relations", defaults={
            'control_group': 'X',
            'format': 'info:fedora/fedora-system:FedoraRELSExt-1.0',
        })
    text = Datastream("TEXT", "Text datastream", defaults={
            'mimetype': 'text/plain',
        })
    extradc = XmlDatastream("EXTRADC", "Managed DC XML datastream", DublinCore,
        defaults={
            'mimetype': 'application/xml',
            'versionable': True,
        })

TEXT_CONTENT = "Here is some text content for a non-xml datastream."
def _add_text_datastream(obj):    
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
        checksumType=ds['checksumType'], versionable=ds['versionable'])
    FILE.close()


class TestDatastreams(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    # save date-time before fixtures are created in fedora
    now = datetime.now(tzutc())   

    def setUp(self):
        super(TestDatastreams, self).setUp()
        self.pid = self.fedora_fixtures_ingested[-1] # get the pid for the last object
        self.obj = MyDigitalObject(self.api, self.pid)

        # add a text datastream to the current test object
        _add_text_datastream(self.obj)

    def test_get_ds_content(self):
        dc = self.obj.dc.content
        self.assert_(isinstance(self.obj.dc, XmlDatastreamObject))
        self.assert_(isinstance(dc, DublinCore))
        self.assertEqual(dc.title, "A partially-prepared test object")
        self.assertEqual(dc.identifier, self.pid)

        self.assert_(isinstance(self.obj.text, DatastreamObject))
        self.assertEqual(self.obj.text.content, TEXT_CONTENT)

    def test_get_ds_info(self):
        self.assertEqual(self.obj.dc.label, "Dublin Core")
        self.assertEqual(self.obj.dc.mimetype, "text/xml")
        self.assertEqual(self.obj.dc.state, "A")
        self.assertEqual(self.obj.dc.versionable, True) 
        self.assertEqual(self.obj.dc.control_group, "X")
        self.assert_(self.now < self.obj.dc.created)

        self.assertEqual(self.obj.text.label, "text datastream")
        self.assertEqual(self.obj.text.mimetype, "text/plain")
        self.assertEqual(self.obj.text.state, "A")
        self.assertEqual(self.obj.text.versionable, False)
        self.assertEqual(self.obj.text.control_group, "M")
        self.assert_(self.now < self.obj.text.created)

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

    def test_undo_last_save(self):
        # test undoing profile and content changes        
        
        # unversioned datastream
        self.obj.text.label = "totally new label"
        self.obj.text.content = "and totally new content, too"
        self.obj.text.save()
        self.assertTrue(self.obj.text.undo_last_save())
        history = self.obj.api.getDatastreamHistory(self.obj.pid, self.obj.text.id)
        self.assertEqual("text datastream", history.datastreams[0].label)
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.text.id)
        self.assertEqual(TEXT_CONTENT, data)
        
        # versioned datastream
        self.obj.dc.label = "DC 2.0"
        self.obj.dc.title = "my new DC"
        self.obj.dc.save()
        self.assertTrue(self.obj.dc.undo_last_save())
        history = self.obj.api.getDatastreamHistory(self.obj.pid, self.obj.dc.id)
        self.assertEqual(1, len(history.datastreams))  # new datastream added, then removed - back to 1 version
        self.assertEqual("Dublin Core", history.datastreams[0].label)
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.dc.id)
        self.assert_('<dc:title>A partially-prepared test object</dc:title>' in data)

        # unversioned - profile change only
        self.obj = MyDigitalObject(self.api, self.pid)
        self.obj.text.label = "totally new label"
        self.obj.text.save()
        self.assertTrue(self.obj.text.undo_last_save())
        history = self.obj.api.getDatastreamHistory(self.obj.pid, self.obj.text.id)
        self.assertEqual("text datastream", history.datastreams[0].label)
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.text.id)
        self.assertEqual(TEXT_CONTENT, data)     
        
class TestNewObject(FedoraTestCase):
    pidspace = TEST_PIDSPACE

    def test_basic_ingest(self):
        self.repo.default_pidspace = self.pidspace
        obj = self.repo.get_object(type=MyDigitalObject)
        obj.save()

        self.assertTrue(isinstance(obj.pid, basestring))
        self.append_test_pid(obj.pid)
        self.assertTrue(obj.pid.startswith(self.pidspace))

        fetched = self.repo.get_object(obj.pid, type=MyDigitalObject)
        self.assertEqual(fetched.dc.content.identifier, obj.pid)

    def test_modified_profile(self):
        obj = self.repo.get_object(type=MyDigitalObject)
        obj.label = 'test label'
        obj.owner = 'tester'
        obj.state = 'I'
        obj.save()
        self.append_test_pid(obj.pid)

        self.assertEqual(obj.label, 'test label')
        self.assertEqual(obj.owner, 'tester')
        self.assertEqual(obj.state, 'I')

        fetched = self.repo.get_object(obj.pid, type=MyDigitalObject)
        self.assertEqual(fetched.label, 'test label')
        self.assertEqual(fetched.owner, 'tester')
        self.assertEqual(fetched.state, 'I')

    def test_default_datastreams(self):
        """If we just create and save an object, verify that DigitalObject
        initializes its datastreams appropriately."""

        obj = self.repo.get_object(type=MyDigitalObject)
        obj.save()
        self.append_test_pid(obj.pid)

        # verify some datastreams on the original object

        # fedora treats dc specially
        self.assertEqual(obj.dc.label, 'Dublin Core')
        self.assertEqual(obj.dc.mimetype, 'text/xml')
        self.assertEqual(obj.dc.versionable, False)
        self.assertEqual(obj.dc.state, 'A')
        self.assertEqual(obj.dc.format, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        self.assertEqual(obj.dc.control_group, 'X')
        self.assertEqual(obj.dc.content.identifier, obj.pid) # fedora sets this automatically

        # test rels-ext as an rdf datastream
        self.assertEqual(obj.rels_ext.label, 'External Relations')
        self.assertEqual(obj.rels_ext.mimetype, 'application/rdf+xml')
        self.assertEqual(obj.rels_ext.versionable, False)
        self.assertEqual(obj.rels_ext.state, 'A')
        self.assertEqual(obj.rels_ext.format, 'info:fedora/fedora-system:FedoraRELSExt-1.0')
        self.assertEqual(obj.rels_ext.control_group, 'X')
        self.assertTrue(isinstance(obj.rels_ext.content, RdfGraph))

        # test managed xml datastreams
        self.assertEqual(obj.extradc.label, 'Managed DC XML datastream')
        self.assertEqual(obj.extradc.mimetype, 'application/xml')
        self.assertEqual(obj.extradc.versionable, True)
        self.assertEqual(obj.extradc.state, 'A')
        self.assertEqual(obj.extradc.control_group, 'M')
        self.assertTrue(isinstance(obj.extradc.content, DublinCore))

        # verify those datastreams on a new version fetched fresh from the
        # repo

        fetched = self.repo.get_object(obj.pid, type=MyDigitalObject)

        self.assertEqual(fetched.dc.label, 'Dublin Core')
        self.assertEqual(fetched.dc.mimetype, 'text/xml')
        self.assertEqual(fetched.dc.versionable, False)
        self.assertEqual(fetched.dc.state, 'A')
        self.assertEqual(fetched.dc.format, 'http://www.openarchives.org/OAI/2.0/oai_dc/')
        self.assertEqual(fetched.dc.control_group, 'X')
        self.assertEqual(fetched.dc.content.identifier, fetched.pid)

        self.assertEqual(fetched.rels_ext.label, 'External Relations')
        self.assertEqual(fetched.rels_ext.mimetype, 'application/rdf+xml')
        self.assertEqual(fetched.rels_ext.versionable, False)
        self.assertEqual(fetched.rels_ext.state, 'A')
        self.assertEqual(fetched.rels_ext.format, 'info:fedora/fedora-system:FedoraRELSExt-1.0')
        self.assertEqual(fetched.rels_ext.control_group, 'X')

        self.assertEqual(fetched.extradc.label, 'Managed DC XML datastream')
        self.assertEqual(fetched.extradc.mimetype, 'application/xml')
        self.assertEqual(fetched.extradc.versionable, True)
        self.assertEqual(fetched.extradc.state, 'A')
        self.assertEqual(fetched.extradc.control_group, 'M')
        self.assertTrue(isinstance(fetched.extradc.content, DublinCore))

    def test_modified_datastreams(self):
        """Verify that we can modify a new object's datastreams before
        ingesting it."""
        obj = MyDigitalObject(self.api, pid=self.getNextPid)
        
        # modify content for dc (metadata should be covered by other tests)
        obj.dc.content.description = 'A test object'
        obj.dc.content.rights = 'Rights? Sure, copy our test object.'

        # modify managed xml content (more metadata in text, below)
        obj.extradc.content.description = 'Still the same test object'

        # rewrite info and content for a managed binary datastream
        obj.text.label = 'The outer limits of testing'
        obj.text.mimetype = 'text/x-test'
        obj.text.versionable = True
        obj.text.state = 'I'
        obj.text.format = 'http://example.com/'
        obj.text.content = 'We are controlling transmission.'

        # save and verify in the same object
        obj.save()
        self.append_test_pid(obj.pid)

        self.assertEqual(obj.dc.content.description, 'A test object')
        self.assertEqual(obj.dc.content.rights, 'Rights? Sure, copy our test object.')
        self.assertEqual(obj.extradc.content.description, 'Still the same test object')
        self.assertEqual(obj.text.label, 'The outer limits of testing')
        self.assertEqual(obj.text.mimetype, 'text/x-test')
        self.assertEqual(obj.text.versionable, True)
        self.assertEqual(obj.text.state, 'I')
        self.assertEqual(obj.text.format, 'http://example.com/')
        self.assertEqual(obj.text.content, 'We are controlling transmission.')

        # re-fetch and verify
        fetched = MyDigitalObject(self.api, obj.pid)

        self.assertEqual(fetched.dc.content.description, 'A test object')
        self.assertEqual(fetched.dc.content.rights, 'Rights? Sure, copy our test object.')
        self.assertEqual(fetched.extradc.content.description, 'Still the same test object')
        self.assertEqual(fetched.text.label, 'The outer limits of testing')
        self.assertEqual(fetched.text.mimetype, 'text/x-test')
        self.assertEqual(fetched.text.versionable, True)
        self.assertEqual(fetched.text.state, 'I')
        self.assertEqual(fetched.text.format, 'http://example.com/')
        self.assertEqual(fetched.text.content, 'We are controlling transmission.')


class TestDigitalObject(FedoraTestCase):
    fixtures = ['object-with-pid.foxml']
    pidspace = TEST_PIDSPACE

    # save date-time before fixtures are created in fedora
    now = datetime.now(tzutc())   

    def setUp(self):
        super(TestDigitalObject, self).setUp()
        self.pid = self.fedora_fixtures_ingested[-1] # get the pid for the last object
        self.obj = MyDigitalObject(self.api, self.pid)
        _add_text_datastream(self.obj)

    def test_properties(self):
        self.assertEqual(self.pid, self.obj.pid)
        self.assertTrue(self.obj.uri.startswith("info:fedora/"))
        self.assertTrue(self.obj.uri.endswith(self.pid))

    def test_get_object_info(self):
        self.assertEqual(self.obj.label, "A partially-prepared test object")
        self.assertEqual(self.obj.owner, "tester")
        self.assertEqual(self.obj.state, "A")
        self.assert_(self.now < self.obj.created)
        self.assert_(self.now < self.obj.modified)

    def test_save_object_info(self):
        self.obj.label = "An updated test object"
        self.obj.owner = "notme"
        self.obj.state = "I"
        saved = self.obj._saveProfile("saving test object profile")
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

        # force an error on saving DC to test backing out text datastream
        self.obj.text.content = "some new text"
        self.obj.dc.content = "this is not dublin core!"    # NOTE: setting xml content like this could change...
        # catch the exception so we can inspect it
        try:
            self.obj.save()
        except DigitalObjectSaveFailure, f:
            save_error = f
        self.assert_(isinstance(save_error, DigitalObjectSaveFailure))
        self.assertEqual(save_error.obj_pid, self.obj.pid,
            "save failure exception should include object pid %s, got %s" % (self.obj.pid, save_error.obj_pid))
        self.assertEqual(save_error.failure, "DC", )
        self.assertEqual(['TEXT', 'DC'], save_error.to_be_saved)
        self.assertEqual(['TEXT'], save_error.saved)
        self.assertEqual(['TEXT'], save_error.cleaned)
        self.assertEqual([], save_error.not_cleaned)
        self.assertTrue(save_error.recovered)
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.text.id)
        self.assertEqual(TEXT_CONTENT, data)

        # force an error updating the profile, should back out both datastreams
        self.obj = MyDigitalObject(self.api, self.pid)
        self.obj.text.content = "some new text"
        self.obj.dc.content.description = "happy happy joy joy"
        # object label is limited in length - force an error with a label that exceeds it
        self.obj.label = ' '.join('too long' for i in range(50))
        try:
            self.obj.save()
        except DigitalObjectSaveFailure, f:
            profile_save_error = f
        self.assert_(isinstance(profile_save_error, DigitalObjectSaveFailure))
        self.assertEqual(profile_save_error.obj_pid, self.obj.pid,
            "save failure exception should include object pid %s, got %s" % (self.obj.pid, save_error.obj_pid))
        self.assertEqual(profile_save_error.failure, "object profile", )
        all_datastreams = ['TEXT', 'DC']
        self.assertEqual(all_datastreams, profile_save_error.to_be_saved)
        self.assertEqual(all_datastreams, profile_save_error.saved)
        self.assertEqual(all_datastreams, profile_save_error.cleaned)
        self.assertEqual([], profile_save_error.not_cleaned)
        self.assertTrue(profile_save_error.recovered)
        # confirm datastreams were reverted back to previous contents
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.text.id)
        self.assertEqual(TEXT_CONTENT, data)
        data, url = self.obj.api.getDatastreamDissemination(self.pid, self.obj.dc.id)
        self.assert_("<dc:description>This object has more data in it than a basic-object.</dc:description>" in data)

        # how to force an error that can't be backed out?

    def test_datastreams_list(self):
        self.assert_("DC" in self.obj.ds_list.keys())
        self.assert_(isinstance(self.obj.ds_list["DC"], ObjectDatastream))
        dc = self.obj.ds_list["DC"]
        self.assertEqual("DC", dc.dsid)
        self.assertEqual("Dublin Core", dc.label)
        self.assertEqual("text/xml", dc.mimeType)

        self.assert_("TEXT" in self.obj.ds_list.keys())
        text = self.obj.ds_list["TEXT"]
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


if __name__ == '__main__':
    main()