#!/usr/bin/env python

import unittest
from os import path

from eulcore.xmlmap import load_xmlobject_from_file, NodeListField
from eulcore.xmlmap.teimap import Tei, TeiSection, TeiDiv, TeiFigure, TeiInterpGroup, TeiInterp, TeiLineGroup, TeiLine, TeiEpigraph, TeiQuote
from testcore import main

class ExtendedTei(Tei):
    # additional mappings for testing
    figure = NodeListField('//tei:figure', TeiFigure)
    interpGroup = NodeListField('//tei:interpGrp', TeiInterpGroup)

class TestTei(unittest.TestCase):
    FIXTURE_FILE = path.join(path.dirname(path.abspath(__file__)) ,
                             'fixtures', 'tei_clarke.xml')
    def setUp(self):
        self.tei = load_xmlobject_from_file(self.FIXTURE_FILE, ExtendedTei)

    def testInit(self):
        self.assert_(isinstance(self.tei, Tei))

    def testBasicFields(self):
        self.assertEqual(self.tei.id, "clarke")
        self.assertEqual(self.tei.title, "A Treasury of War Poetry: Electronic Edition")
        #self.assertEqual(self.tei.author, "Various")
        self.assertEqual(self.tei.editor, "George Herbert Clarke")

        self.assert_(isinstance(self.tei.front, TeiSection))
        self.assert_(isinstance(self.tei.body, TeiSection))
        self.assert_(isinstance(self.tei.back, TeiSection))

        self.assert_(isinstance(self.tei.body.div[0], TeiDiv))

    def testTeiDiv(self):
        div = self.tei.body.div[0]
        self.assertEqual('clarke005', div.id)
        self.assertEqual('Chapter', div.type)
        self.assertEqual('America', div.title)
        # reference to document-level info
        self.assertEqual('A Treasury of War Poetry: Electronic Edition', div.doctitle)
        self.assertEqual('clarke', div.doc_id)

        # subdiv (recursive mapping)
        self.assert_(isinstance(div.div[0], TeiDiv))
        self.assertEqual('clarke006', div.div[0].id)
        self.assertEqual('The Choice', div.div[0].title[0])
        self.assertEqual('Rudyard Kipling', div.div[0].author)

        self.assert_("THE RIVERSIDE PRESS LIMITED, EDINBURGH" in self.tei.back.div[1].text)

    def testTeiFigure(self):
        self.assert_(isinstance(self.tei.figure[0], TeiFigure))
        self.assertEqual("chateau_thierry2", self.tei.figure[0].entity)
        self.assertEqual("Chateau-Thierry", self.tei.figure[0].head)
        self.assertEqual("nat-fr mil-f con-r im-ph t-wwi", self.tei.figure[0].ana)
        self.assert_("photo of ruined houses" in self.tei.figure[0].description)

    def testTeiInterpGroup(self):
        self.assert_(isinstance(self.tei.interpGroup[0], TeiInterpGroup))
        self.assert_(isinstance(self.tei.interpGroup[0].interp[0], TeiInterp))
        self.assertEqual("image", self.tei.interpGroup[0].type)
        self.assertEqual("time period", self.tei.interpGroup[1].type)
        self.assertEqual("im-ph", self.tei.interpGroup[0].interp[0].id)
        self.assertEqual("photo", self.tei.interpGroup[0].interp[0].value)
        self.assertEqual("mil-na", self.tei.interpGroup[2].interp[1].id)


    def testTeiLineGroup(self):
        poem = self.tei.body.div[0].div[2] #using clarke008
        self.assert_(isinstance(poem.linegroup[0], TeiLineGroup))
        self.assert_(isinstance(poem.linegroup[0].line[0], TeiLine))
        self.assertEqual(4, poem.linegroup[1].line[3].indent())
        self.assertEqual(0, poem.linegroup[0].line[2].indent())
       # print poem.linegroup[0].line[2].indent()

        
    def testTeiEpigraph(self):
        epigraph = self.tei.front.div[1].epigraph[0] #using clarke002
        self.assertEqual("epigraph", self.tei.front.div[1].type)
        self.assert_(isinstance(epigraph, TeiEpigraph))
        self.assert_(isinstance(epigraph.quote[0], TeiQuote))
        self.assert_(isinstance(epigraph.quote[0].line[0], TeiLine))

        
if __name__ == '__main__':
    main()
