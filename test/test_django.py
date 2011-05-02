#!/usr/bin/env python

import sys
from django.core.management import setup_environ
from testcore import tests_from_modules

# django test modules that aren't in apps go here
non_app_test_modules = (
    'eulcore.django.non_app_tests',
    'eulcore.django.fedora.tests',
    )
def non_app_tests():
    return tests_from_modules(non_app_test_modules)

def run_django_tests(argv=None, extras=[]):
    # this code inlined (with simplifications) from relevant manage.py code
    
    argv = argv or sys.argv[:]
    # 0 is script name      (is this always true?)
    test_apps = argv[1:]    # pass any args as param to run_tests - apps to be tested

    # use our settings file to bootstrap the test environment, then switch
    # to the official one.
    setup_test_environ()

    if test_apps and test_apps[0] == 'shell':
        _execute_manager(argv)
    else:
        # if they didn't specify particular test apps to run, then assume
        # they want all of them, including the non_app_tests()
        if not test_apps:
            extras = non_app_tests() + extras

        if _execute_tests(test_apps, extras):
            sys.exit(1)

def setup_test_environ():
    from django_tester import settings
    setup_environ(settings)

def _execute_tests(test_apps=[], extras=[]):
    from django.conf import settings

    # FIXME: if we don't import existdb here, starting_tests doesn't get
    # triggered for some reason
    from django.test.utils import get_runner
    from django.test.simple import DjangoTestSuiteRunner
    
    from eulcore.django.testsetup import starting_tests, finished_tests
    import eulcore.django.existdb

    starting_tests.send(None)
    django_runner = get_runner(settings)
    # in older versions of django and xmlrunner, get_runner returns a run_tests method
    # newer versions of django and xmlrunner, get_runner returns a class like DjangoTestSuiteRunner
    if hasattr(django_runner, 'run_tests'):
        django_runner = django_runner(verbosity=1, interactive=True).run_tests

    failures = django_runner(test_labels=test_apps, interactive=True, 
                extra_tests=extras)
    finished_tests.send(None)

    return failures

def _execute_manager(argv=None):
    from django.core.management import ManagementUtility
    utility = ManagementUtility(argv)
    utility.execute()

if __name__ == '__main__':
    run_django_tests()
