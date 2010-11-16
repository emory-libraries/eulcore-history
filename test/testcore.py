import unittest

def tests_from_modules(modnames):
    return [ unittest.findTestCases(__import__(modname, fromlist=['*']))
             for modname in modnames ]

def main(testRunner=unittest.TextTestRunner, *args, **kwargs):
    try:
        import xmlrunner
        testRunner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass
    unittest.main(testRunner=testRunner, *args, **kwargs)
