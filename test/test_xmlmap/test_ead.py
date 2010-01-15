import unittest
from os import path

from eulcore.xmlmap  import load_xmlobject_from_file, XPathString
from eulcore.xmlmap.eadmap import ead

class TestEad(unittest.TestCase):
    FIXTURE_FILE = path.join(path.dirname(path.abspath(__file__)) ,
                             'fixtures', 'heaney653.xml')
    def setUp(self):
        self.ead = load_xmlobject_from_file(self.FIXTURE_FILE, ead)

    def testInit(self):
        self.assert_(isinstance(self.ead, ead))

    def testBasicFields(self):
        self.assertEqual(self.ead.title, "Seamus Heaney collection, 1972-1997")
        self.assertEqual(self.ead.author, "Manuscript, Archives, and Rare Book Library, Emory University")
        # whitespace makes fields with tags a bit messier...
        self.assert_("Seamus Heaney collection," in self.ead.unittitle)
        self.assert_("1972-2005" in self.ead.unittitle)
        # several different extents in the physical description
        self.assert_("1 linear ft." in self.ead.physical_desc)
        self.assert_("(3 boxes)" in self.ead.physical_desc)
        self.assert_("12 oversized papers (OP)" in self.ead.physical_desc)
        self.assert_("materials relating to Irish poet Seamus Heaney" in self.ead.abstract)

        
if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner)
