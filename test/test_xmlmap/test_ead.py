#!/usr/bin/env python

import unittest
from os import path

from eulcore.xmlmap  import load_xmlobject_from_file, load_xmlobject_from_string
#from eulcore.xmlmap.eadmap import EncodedArchivalDescription, ArchivalDescription, ControlledAccessHeadings, Section, Heading, SubordinateComponents, Component
from eulcore.xmlmap.eadmap import *
from testcore import main

class TestEad(unittest.TestCase):
    FIXTURE_FILE = path.join(path.dirname(path.abspath(__file__)) ,
                             'fixtures', 'heaney653.xml')
    def setUp(self):
        self.ead = load_xmlobject_from_file(self.FIXTURE_FILE, EncodedArchivalDescription)

    def testInit(self):
        self.assert_(isinstance(self.ead, EncodedArchivalDescription))

    def testBasicFields(self):
        self.assertEqual(unicode(self.ead.title), "Seamus Heaney collection, 1972-1997")
        self.assertEqual(self.ead.eadid, "heaney653.xml")
        self.assertEqual(self.ead.id, "heaney653-011")
        self.assertEqual(self.ead.author, "Manuscript, Archives, and Rare Book Library, Emory University")
        # whitespace makes fields with tags a bit messier...
        self.assert_("Seamus Heaney collection," in unicode(self.ead.unittitle))
        self.assert_("1972-2005" in unicode(self.ead.unittitle))
        # several different extents in the physical description;
        # FIXME: all smashed together
        self.assert_("1 linear ft." in self.ead.physical_desc)
        self.assert_("(3 boxes)" in self.ead.physical_desc)
        self.assert_("12 oversized papers (OP)" in self.ead.physical_desc)
        self.assert_("materials relating to Irish poet Seamus Heaney" in unicode(self.ead.abstract))

    def test_ArchivalDescription(self):
        self.assert_(isinstance(self.ead.archdesc, ArchivalDescription))
        ad = self.ead.archdesc
        self.assert_("Heaney, Seamus, 1939-" in ad.origination)  #whitespace variance
        self.assertEqual("Manuscript Collection No.653", ad.unitid)
        self.assertEqual("Manuscript Collection No.653", ad.unitid)
        self.assertEqual("1 linear ft.", ad.extent[0])
        self.assertEqual("(3 boxes)", ad.extent[1])
        self.assertEqual("12 oversized papers (OP)", ad.extent[2])
        self.assertEqual("Materials entirely in English.", ad.langmaterial)
        self.assertEqual("In the Archives.", ad.location)
        self.assert_(isinstance(ad.access_restriction, Section))
        self.assertEqual("Restrictions on access", ad.access_restriction.head)
        self.assert_("Special restrictions apply" in unicode(ad.access_restriction.content[0]))
        self.assert_(isinstance(ad.use_restriction, Section))
        self.assertEqual("Terms Governing Use and Reproduction", ad.use_restriction.head)
        self.assert_("limitations noted in departmental policies" in unicode(ad.use_restriction.content[0]))
        self.assert_(isinstance(ad.alternate_form, Section))
        self.assertEqual("Publication Note", ad.alternate_form.head)
        self.assert_("Published in" in unicode(ad.alternate_form.content[0]))
        self.assert_(isinstance(ad.originals_location, Section))
        self.assertEqual("Location of Originals", ad.originals_location.head)
        self.assert_("Suppressed chapter" in unicode(ad.originals_location.content[0]))
        self.assert_(isinstance(ad.related_material, Section))
        self.assertEqual("Related Materials in This Repository", ad.related_material.head)
        self.assert_("part of MSS" in unicode(ad.related_material.content[0]))
        self.assert_(isinstance(ad.separated_material, Section))
        self.assertEqual("Related Materials in This Repository", ad.separated_material.head)
        self.assert_("Ciaran Carson papers, Peter Fallon" in unicode(ad.separated_material.content[0]))
        self.assert_(isinstance(ad.acquisition_info, Section))
        self.assertEqual("Source", ad.acquisition_info.head)
        self.assert_("Collection assembled from various sources." in unicode(ad.acquisition_info.content[0]))
        self.assert_(isinstance(ad.custodial_history, Section))
        self.assertEqual("Custodial History", ad.custodial_history.head)
        self.assert_("Originally received as part of" in unicode(ad.custodial_history.content[0]))
        self.assert_(isinstance(ad.preferred_citation, Section))
        self.assertEqual("Citation", ad.preferred_citation.head)
        self.assert_("[after identification of item(s)" in unicode(ad.preferred_citation.content[0]))
        self.assert_(isinstance(ad.biography_history, Section))
        self.assertEqual("Biographical Note", ad.biography_history.head)
        self.assert_("born on April 13" in unicode(ad.biography_history.content[0]))
        self.assert_("While at St. Joseph's" in unicode(ad.biography_history.content[1]))
        self.assert_(isinstance(ad.bibliography, Section))
        self.assertEqual("Publication Note", ad.bibliography.head)
        self.assert_("Susan Jenkins Brown" in unicode(ad.bibliography.content[0]))
        self.assert_(isinstance(ad.scope_content, Section))
        self.assertEqual("Scope and Content Note", ad.scope_content.head)
        self.assert_("consists of materials relating" in unicode(ad.scope_content.content[0]))
        self.assert_(isinstance(ad.arrangement, Section))
        self.assertEqual("Arrangement Note", ad.arrangement.head)
        self.assert_("five series" in unicode(ad.arrangement.content[0]))
        self.assert_(isinstance(ad.other, Section))
        self.assertEqual("Finding Aid Note", ad.other.head)
        self.assert_("Index to selected correspondents" in unicode(ad.other.content[0]))

    def test_index_indexentry(self):
        ad = self.ead.archdesc
        # index and indexentry
        self.assertEqual(2, len(ad.index))
        index = ad.index[0]
        self.assert_(isinstance(index, Index))
        self.assertEqual("Index of Selected Correspondents", index.head)
        self.assertEqual("index1", index.id)
        self.assert_("relates to the correspondence in Series 1" in index.note.content[0])
        self.assertEqual(2, len(index.entry))
        self.assert_(isinstance(index.entry[0], IndexEntry))
        self.assertEqual("Batten, Guinn", index.entry[0].name)
        self.assert_(isinstance(index.entry[0].ptrgroup, PointerGroup))
        self.assertEqual(3, len(index.entry[0].ptrgroup.ref))
        self.assert_(isinstance(index.entry[0].ptrgroup.ref[0], Reference))
        self.assertEqual("simple", index.entry[0].ptrgroup.ref[0].type)
        self.assert_("1995 July" in index.entry[0].ptrgroup.ref[0].value)
        self.assertEqual("Belton, Neil", index.entry[1].name)
        self.assert_("1993 November 3" in index.entry[1].ptrgroup.ref[-1].value)

        # multiple indexes
        self.assert_(isinstance(ad.index[1], Index))
        self.assertEqual("Second Index", ad.index[1].head)
        self.assertEqual("index2", ad.index[1].id)


        

    def test_ControlledAccessHeadings(self):
        ca = self.ead.archdesc.controlaccess
        self.assert_(isinstance(ca, ControlledAccessHeadings))
        self.assertEqual("Selected Search Terms", ca.head)
        self.assert_(isinstance(ca.controlaccess[0], ControlledAccessHeadings))
        self.assertEqual("Personal Names", ca.controlaccess[0].head)
        self.assert_(isinstance(ca.controlaccess[0].person_name[0], Heading))
        self.assertEqual("Barker, Sebastian.", ca.controlaccess[0].person_name[0].value)
        self.assert_(isinstance(ca.controlaccess[0].family_name[0], Heading))
        self.assertEqual("Dozier family.", ca.controlaccess[0].family_name[0].value)
        self.assertEqual("English poetry--Irish authors--20th century.", ca.controlaccess[1].subject[0].value)
        self.assertEqual("Ireland.", ca.controlaccess[2].geographic_name[0].value)
        self.assertEqual("Manuscripts.", ca.controlaccess[3].genre_form[0].value)
        self.assertEqual("Poet.", ca.controlaccess[4].occupation[0].value)
        self.assert_(isinstance(ca.controlaccess[5].corporate_name[0], Heading))
        self.assertEqual("Irish Academy of Letters", ca.controlaccess[5].corporate_name[0].value)
        self.assert_(isinstance(ca.controlaccess[6].function[0], Heading))
        self.assertEqual("Law enforcing.", ca.controlaccess[6].function[0].value)
        self.assert_(isinstance(ca.controlaccess[7].title[0], Heading))
        self.assertEqual("New Yorker (New York, 1925-)", ca.controlaccess[7].title[0].value)

        # terms -  mapps to all types, mixed, in the order they appear
        all_terms = ca.controlaccess[8].terms
        self.assertEqual("title", all_terms[0].value)
        self.assertEqual("person", all_terms[1].value)
        self.assertEqual("family", all_terms[2].value)
        self.assertEqual("corp", all_terms[3].value)
        self.assertEqual("occupation", all_terms[4].value)
        self.assertEqual("subject", all_terms[5].value)
        self.assertEqual("geography", all_terms[6].value)
        self.assertEqual("genre", all_terms[7].value)
        self.assertEqual("function", all_terms[8].value)

    def test_SubordinateComponents(self):
        dsc = self.ead.dsc
        self.assert_(isinstance(dsc, SubordinateComponents))
        self.assertEqual("combined", dsc.type)
        self.assertEqual("Description of Series", dsc.head)
        # c01 - series
        self.assert_(isinstance(dsc.c[0], Component))
        self.assertEqual("series", dsc.c[0].level)
        self.assert_(isinstance(dsc.c[0].did, DescriptiveIdentification))
        self.assertEqual("Series 1", dsc.c[0].did.unitid)
        self.assertEqual("Writings by Seamus Heaney", unicode(dsc.c[0].did.unittitle))
        self.assertEqual("Box 1: folders 1-12", dsc.c[0].did.physdesc)
        # c02 - file
        self.assert_(isinstance(dsc.c[0].c[0], Component))
        self.assertEqual("file", dsc.c[0].c[0].level)
        self.assert_(isinstance(dsc.c[0].c[0].did, DescriptiveIdentification))        
        self.assert_("holograph manuscript" in unicode(dsc.c[0].c[0].did.unittitle))
        self.assertEqual("box", dsc.c[0].c[0].did.container[0].type)
        self.assertEqual("1", dsc.c[0].c[0].did.container[0].value)
        self.assertEqual("folder", dsc.c[0].c[0].did.container[1].type)
        self.assertEqual("1", dsc.c[0].c[0].did.container[1].value)

        self.assertTrue(dsc.hasSeries())
        self.assertFalse(dsc.c[0].hasSubseries())

        # second series has a subseries
        self.assertTrue(dsc.c[1].hasSubseries())
        # access c03 level item
        self.assertEqual("file", dsc.c[1].c[0].c[0].level)
        self.assert_("Hilary Boyle" in unicode(dsc.c[1].c[0].c[0].did.unittitle))

    def test_SubordinateComponents_noseries(self):
        # simple finding aid with no series but only a container list
        simple_dsc = """<dsc><c01 level="file"/></dsc>"""
        dsc = load_xmlobject_from_string(simple_dsc, SubordinateComponents)
        self.assertFalse(dsc.hasSeries())

    def test_FileDescription(self):
        filedesc = self.ead.file_desc
        self.assert_(isinstance(filedesc, FileDescription))
        self.assert_(isinstance(filedesc.publication, PublicationStatement))
        self.assert_(isinstance(filedesc.publication.address, Address))
        self.assertEqual("Emory University", filedesc.publication.publisher)
        self.assertEqual("May 5, 2005", filedesc.publication.date)
        self.assertEqual("Robert W. Woodruff Library", filedesc.publication.address.lines[0])
        self.assertEqual("404-727-6887", filedesc.publication.address.lines[3])
        self.assertEqual("marbl@emory.edu", filedesc.publication.address.lines[-1])
    
    def test_ProfileDescription(self):
        profiledesc = self.ead.profiledesc
        self.assertEqual("English", profiledesc.language)


        
if __name__ == '__main__':
    main()
