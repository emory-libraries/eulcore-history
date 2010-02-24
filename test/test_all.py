#!/usr/bin/env python

import unittest
import sys
from django.core.management import setup_environ

from django_tester import settings

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
    # this code inlined (with simplifications) from relevant manage.py code
    setup_environ(settings)

    from django.test.utils import get_runner
    django_runner = get_runner(settings)
    failures = django_runner(None, verbosity=1, interactive=True,
            extra_tests=non_django_tests())
    if failures:
        sys.exit(failures)
