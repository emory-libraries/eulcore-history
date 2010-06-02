from urlparse import urlsplit

# use test database settings from non-django existdb test
#from test_existdb import settings as exist_settings
from test_existdb.test_db import EXISTDB_SERVER_URL, EXISTDB_ROOT_COLLECTION, EXISTDB_TEST_COLLECTION

# Django settings for eulcore project.
DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

#We will not be using a RDB but this will allow tests to run
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'no_db'

# eXist DB settings imported above

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '%p=r8r%&a7$e2y8)w2fh+&@)duz!3=ps82t^x^p9w)-u2#@h8#'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = ''

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    # needed for test dependencies:
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    # our apps to test:
    'eulcore.django.existdb',
    'eulcore.django.testsetup',
    'eulcore.django.ldap',
)

try:
    # use xmlrunner if it's installed; default runner otherwise. download
    # it from http://github.com/danielfm/unittest-xml-reporting/ to output
    # test results in JUnit-compatible XML.
    import xmlrunner
    TEST_RUNNER='xmlrunner.extra.djangotestrunner.run_tests'
    TEST_OUTPUT_DIR='test-results'
except ImportError:
    pass
