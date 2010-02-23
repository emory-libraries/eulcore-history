#!/usr/bin/env python

import unittest
from testcore import main

# add any new modules to be tested here
modules_to_test = (
    'test_existdb',
    'test_fedora',
    'test_xmlmap', 
    )


def suite():
    alltests = unittest.TestSuite()
    for module_name in modules_to_test:
        module = __import__(module_name)
        alltests.addTest(unittest.findTestCases(module))
    return alltests

if __name__ == '__main__':
    main(defaultTest='suite')
