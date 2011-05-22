#!/usr/bin/env python

# use this script to test django non-application tests without running all tests

import unittest
import os

# this setting is required before loading the eulcore.django import
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_tester.settings' 
#from eulcore.django.non_app_tests import *
from testcore import tests_from_modules
from test_django import run_django_tests, non_app_tests

if __name__ == '__main__':
    # sort of cheating here: run only http tests (because it is short)
    # then use extras to run the tests we actually want here
    run_django_tests([__file__, 'http'], extras=non_app_tests())
