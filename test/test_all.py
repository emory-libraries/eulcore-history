#!/usr/bin/env python

import unittest

from test_django import run_django_tests

# add any non-django modules to be tested here
non_django_test_modules = (
    'test_existdb',
    'test_fedora',
    'test_xmlmap', 
    )

def non_django_tests():
    for module_name in non_django_test_modules:
        module = __import__(module_name)
        yield unittest.findTestCases(module)

if __name__ == '__main__':
    run_django_tests(extras=non_django_tests())
