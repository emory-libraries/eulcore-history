#!/usr/bin/env python

import os
import unittest
import logging.config

from testcore import tests_from_modules, get_testsuite_runner

test_modules = (
    'test_binfile',
    'test_djangoextras', 
    )

if __name__ == '__main__':
    # load logging config, if any
    test_dir = os.path.dirname(os.path.abspath(__file__))
    LOGGING_CONF = os.path.join(test_dir, 'logging.conf')
    if os.path.exists(LOGGING_CONF):
        logging.config.fileConfig(LOGGING_CONF)

    # generate test suite from test modules
    alltests = unittest.TestSuite(
        (unittest.TestLoader().loadTestsFromName(mod) for mod in test_modules)
    )
    
    test_runner = get_testsuite_runner()
    # djangoextras code aren't django apps per-se, so just run them as extra tests
    test_runner.run_tests([], extra_tests=alltests)
