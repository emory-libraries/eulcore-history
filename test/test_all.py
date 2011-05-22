#!/usr/bin/env python

import os
import unittest
import logging.config

from testcore import tests_from_modules
from test_django import run_django_tests

# anybody who references django needs this before loading
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_tester.settings'

# add any non-django modules to be tested here
non_django_test_modules = (
    )
def non_django_tests():
    return tests_from_modules(non_django_test_modules)

if __name__ == '__main__':
    test_dir = os.path.dirname(os.path.abspath(__file__))
    LOGGING_CONF = os.path.join(test_dir, 'logging.conf')
    if os.path.exists(LOGGING_CONF):
        logging.config.fileConfig(LOGGING_CONF)

    run_django_tests(extras=non_django_tests())
