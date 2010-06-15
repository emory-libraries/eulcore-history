#!/usr/bin/env python

import sys
from django.core.management import setup_environ
from django.test.simple import DjangoTestSuiteRunner

def run_django_tests(argv=None, extras=None):
    # this code inlined (with simplifications) from relevant manage.py code
    
    argv = argv or sys.argv[:]
    # 0 is script name      (is this always true?)
    test_apps = argv[1:]    # pass any args as param to run_tests - apps to be tested

    # use our settings file to bootstrap the test environment, then switch
    # to the official one.
    from django_tester import settings
    setup_environ(settings)
    from django.conf import settings

    # FIXME: if we don't import existdb here, starting_tests doesn't get
    # triggered for some reason
    from django.test.utils import get_runner
    from eulcore.django.testsetup import starting_tests, finished_tests
    import eulcore.django.existdb

    starting_tests.send(None)
    django_runner = get_runner(settings)
    # in django 1.2, if xmlrunner is not installed, get_runner returns DjangoTestSuiteRunner    
    if django_runner == DjangoTestSuiteRunner:
        django_runner = django_runner(verbosity=1, interactive=True).run_tests

    failures = django_runner(test_labels=test_apps, interactive=True, 
                extra_tests=extras)
    finished_tests.send(None)

    if failures:
        sys.exit(failures)

if __name__ == '__main__':
    run_django_tests()
