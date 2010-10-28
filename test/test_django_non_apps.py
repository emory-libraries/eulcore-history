#!/usr/bin/env python

# use this script to test django non-application tests without running all tests

import unittest
import os
# this setting is required before loading the eulcore.django import
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_tester.settings' 
from eulcore.django.non_app_tests import *
from test_django import run_django_tests

def django_non_app_tests():
    import eulcore.django.non_app_tests
    yield unittest.findTestCases(eulcore.django.non_app_tests)

if __name__ == '__main__':

    # sort of cheating here: run only http tests (because it is short)
    # then use extras to run the tests we actually want here
    run_django_tests([__name__, 'http'], extras=django_non_app_tests())
