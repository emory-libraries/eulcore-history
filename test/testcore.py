import unittest

def main(testRunner=unittest.TextTestRunner, *args, **kwargs):
    try:
        import xmlrunner
        testRunner = xmlrunner.XMLTestRunner(output='test-results')
    except ImportError:
        pass
    unittest.main(testRunner=testRunner, *args, **kwargs)
