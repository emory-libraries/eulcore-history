#!/usr/bin/env python

import unittest
from os import path

from eulcore.xmlmap  import load_xmlobject_from_file
from eulcore.xmlmap.teimap import Tei, TeiSection, TeiDiv

class TestTei(unittest.TestCase):
    FIXTURE_FILE = path.join(path.dirname(path.abspath(__file__)) ,
                             'fixtures', 'tei_clarke.xml')
    def setUp(self):
        self.tei = load_xmlobject_from_file(self.FIXTURE_FILE, Tei)

    def testInit(self):
        self.assert_(isinstance(self.tei, Tei))

    def testBasicFields(self):
        self.assertEqual(self.tei.id, "clarke")
        self.assertEqual(self.tei.title, "A Treasury of War Poetry: Electronic Edition")
        self.assertEqual(self.tei.author, "Various")
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
        self.assertEqual('The Choice', div.div[0].title)
        self.assertEqual('Rudyard Kipling', div.div[0].author)
        

if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner)


