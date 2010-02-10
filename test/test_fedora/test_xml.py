#!/usr/bin/env python

import os
import unittest

from eulcore.fedora.xml import DigitalObject
from eulcore.xmlmap import load_xmlobject_from_file
from test_fedora.base import fixture_path

class TestFoxml(unittest.TestCase):
    def setUp(self):
        obj_path = fixture_path('object-with-pid.foxml')
        self.object = load_xmlobject_from_file(obj_path, DigitalObject)

    def testGetFields(self):
        self.assertEqual(self.object.pid, 'changeme:42')


if __name__ == '__main__':
    runner = unittest.TextTestRunner
    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass
    unittest.main(testRunner=runner)
