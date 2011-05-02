from urlparse import urlsplit

# use test database settings from non-django existdb test
#from test_existdb import settings as exist_settings
from test_existdb.test_db import EXISTDB_SERVER_URL, EXISTDB_ROOT_COLLECTION, \
     EXISTDB_TEST_COLLECTION, EXISTDB_SERVER_USER, EXISTDB_SERVER_PASSWORD

from os import path

# Get the directory of this file for relative dir paths.
# Django sets too many absolute paths.
BASE_DIR = path.dirname(path.abspath(__file__))



# Django settings for eulcore project.
DEBUG = True
TEMPLATE_DEBUG = False

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

ROOT_URLCONF = 'django_tester.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    path.join(BASE_DIR, 'templates'),
)

INSTALLED_APPS = (
    # our apps to test:
    'eulcore.django.auth',
    'eulcore.django.emory_ldap',
    'eulcore.django.existdb',
    'eulcore.django.fedora',
    'eulcore.django.forms',
    'eulcore.django.http',
    'eulcore.django.ldap',
    'djcelery',
    'eulcore.django.taskresult',
    'eulcore.django.testsetup',

    # needed for test dependencies:
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
)

AUTH_PROFILE_MODULE = 'emory_ldap.EmoryLDAPUserProfile'



# celery config for taskresult
CELERY_ALWAYS_EAGER = True
import djcelery
djcelery.setup_loader()

BROKER_HOST = "localhost" # e.g "localhost"
BROKER_PORT =  '5672'  # e.g 5672
BROKER_USER = "guest" # e.g "user"
BROKER_PASSWORD = "guest" #e.g. "password"
BROKER_VHOST = "/" # e.g. "digitalmasters_vhost"
CELERY_RESULT_BACKEND = "database" # e.g "amqp"


from test_fedora.base import FEDORA_ROOT, FEDORA_USER, FEDORA_PASS, FEDORA_PIDSPACE
# store fedora fixture dir so fixtures can be shared with django and non-django fedora tests
from test_fedora import base as test_fedora_base
FEDORA_FIXTURES_DIR = path.join(path.dirname(path.abspath(test_fedora_base.__file__)), 'fixtures')

try:
    # use xmlrunner if it's installed; default runner otherwise. download
    # it from http://github.com/danielfm/unittest-xml-reporting/ to output
    # test results in JUnit-compatible XML.
    import xmlrunner
    TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'
    # NOTE: older versions of xmlrunner require using this syntax:
    # TEST_RUNNER='xmlrunner.extra.djangotestrunner.run_tests'
    TEST_OUTPUT_DIR='test-results'
    TEST_OUTPUT_VERBOSE = True
    TEST_OUTPUT_DESCRIPTIONS = True
    print "DEBUG: test runner is ", TEST_RUNNER
except ImportError:
    pass
