#!/usr/bin/env python

import sys
from django.core.management import setup_environ

from django_tester import settings

if __name__ == '__main__':
    # this code inlined (with simplifications) from relevant manage.py code
    setup_environ(settings)

    # FIXME: if we don't import existdb here, starting_tests doesn't get
    # triggered for some reason
    from django.test.utils import get_runner
    from eulcore.django.testsetup import starting_tests, finished_tests
    import eulcore.django.existdb

    starting_tests.send(None)
    django_runner = get_runner(settings)
    failures = django_runner(None, verbosity=1, interactive=True)
    finished_tests.send(None)

    if failures:
        sys.exit(failures)
