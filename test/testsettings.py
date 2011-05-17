# django settings file

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'eulcommon-test.db'
    }
}


# suppress normal template context processing
# for tests that render templates
TEMPLATE_CONTEXT_PROCESSORS = []

# output dir for xml tests
TEST_OUTPUT_DIR = 'test-results'
