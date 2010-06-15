#!/usr/bin/env python

import sys
from django.core.management import setup_environ

if __name__ == '__main__':
    # this code inlined (with simplifications) from relevant manage.py code

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
    # in django 1.2, get_runner returns DjangoTestSuiteRunner
    django_runner = get_runner(settings)(verbosity=1, interactive=True)
    failures = django_runner.run_tests(test_labels=None)    # run all installed apps
    finished_tests.send(None)

    if failures:
        sys.exit(failures)
