#!/usr/bin/env python

import sys
from django.core.management import setup_environ

from django_tester import settings

if __name__ == '__main__':
    # this code inlined (with simplifications) from relevant manage.py code
    setup_environ(settings)

    from django.test.utils import get_runner
    django_runner = get_runner(settings)
    failures = django_runner(None, verbosity=1, interactive=True)
    if failures:
        sys.exit(failures)
