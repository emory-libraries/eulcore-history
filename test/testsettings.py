from localsettings import *

EXISTDB_SERVER_PROTOCOL = "http://"
EXISTDB_SERVER_HOST     = "kamina.library.emory.edu:8080/exist"
# NOTE: test account used for tests that require non-guest access; user should be in eXist DBA group
EXISTDB_SERVER_USER     = "eulcore_tester"
EXISTDB_SERVER_PASSWORD = "eVlc0re_t3st"
# main access - no user/password, guest account
EXISTDB_SERVER_URL = EXISTDB_SERVER_PROTOCOL + EXISTDB_SERVER_HOST
# access with the specified user account
EXISTDB_SERVER_URL_DBA      = EXISTDB_SERVER_PROTOCOL + EXISTDB_SERVER_USER + ":" + \
    EXISTDB_SERVER_PASSWORD + "@" + EXISTDB_SERVER_HOST
EXISTDB_ROOT_COLLECTION = '/eulcore'
# NOTE: currently, for full-text query tests to work, test collection should be named /test/something
#       a system collection named /db/system/config/db/test should exist and be writable by guest
EXISTDB_TEST_COLLECTION = '/test' + EXISTDB_ROOT_COLLECTION
