#!/usr/bin/env python

import os
import unittest
from testcore import tests_from_modules
from test_django import run_django_tests

# anybody who references django needs this before loading
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_tester.settings'

# add any non-django modules to be tested here
non_django_test_modules = (
    'test_existdb',
    'test_fedora',
    'test_xmlmap', 
    'test_xpath',
    )
def non_django_tests():
    return tests_from_modules(non_django_test_modules)

if __name__ == '__main__':
    run_django_tests(extras=non_django_tests())
