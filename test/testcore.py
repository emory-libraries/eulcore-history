import unittest

import os
# must be set before importing anything from django
os.environ['DJANGO_SETTINGS_MODULE'] = 'testsettings'

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

def tests_from_modules(modnames):
    return [ unittest.findTestCases(__import__(modname, fromlist=['*']))
             for modname in modnames ]

def get_test_runner(runner=unittest.TextTestRunner()):
    # use xmlrunner if available; otherwise, fall back to text runner
    try:
        import xmlrunner
        runner = xmlrunner.XMLTestRunner(output=settings.TEST_OUTPUT_DIR)
    except ImportError:
        pass
    return runner

def get_testsuite_runner(runner=DjangoTestSuiteRunner()):
    # use xmlrunner if available; otherwise, fall back to text runner

    try:
        import xmlrunner.extra.djangotestrunner
        runner = xmlrunner.extra.djangotestrunner.XMLTestRunner()
        # when running as a suite, output dir must be set in django settings
    except ImportError:
        pass
    return runner
    

def main(testRunner=None, *args, **kwargs):
    if testRunner is None:
        testRunner = get_test_runner()

    unittest.main(testRunner=testRunner, *args, **kwargs)
