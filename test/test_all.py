#!/usr/bin/env python

import unittest

# add any new modules to be tested here
modules_to_test = ('test_xmlmap', 'test_existdb')


def suite():
    alltests = unittest.TestSuite()
    for module in map(__import__, modules_to_test):
        alltests.addTest(unittest.findTestCases(module))
    return alltests

if __name__ == '__main__':
    runner = unittest.TextTestRunner

    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass

    unittest.main(testRunner=runner,defaultTest='suite')

