# file django\existdb\__init__.py
# 
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from eulcore.django.testsetup import starting_tests, finished_tests
from eulcore.django.existdb.db import ExistDB, ExistDBException
from django.conf import settings

_stored_default_collection = None

def _use_test_collection(sender, **kwargs):    
    global _stored_default_collection
    _stored_default_collection = getattr(settings, "EXISTDB_ROOT_COLLECTION", None)

    if getattr(settings, "EXISTDB_TEST_COLLECTION", None):
        settings.EXISTDB_ROOT_COLLECTION = settings.EXISTDB_TEST_COLLECTION
    else:
        settings.EXISTDB_ROOT_COLLECTION = getattr(settings, "EXISTDB_ROOT_COLLECTION", "/default") + "_test"

    print "Creating eXist Test Collection: %s" % settings.EXISTDB_ROOT_COLLECTION
    # now that existdb root collection has been set to test collection, init db connection
    db = ExistDB()
    # create test collection (don't complain if collection already exists)
    db.createCollection(settings.EXISTDB_ROOT_COLLECTION, True)


def _restore_root_collection(sender, **kwargs):
    global _stored_default_collection
    # if use_test_collection didn't run, don't change anything
    if _stored_default_collection is None:
        print "eXist test-start handler does not appear to have run; not restoring eXist Root Collection"
        print "Is 'eulcore.django.existdb' in your installed apps?"
    else:
        print "Removing eXist Test Collection: %s" % settings.EXISTDB_ROOT_COLLECTION
        # before restoring existdb non-test root collection, init db connection
        db = ExistDB()
        try:            
            # remove test collection
            db.removeCollection(settings.EXISTDB_ROOT_COLLECTION)
        except ExistDBException, e:
            print "Error removing collection ", settings.EXISTDB_ROOT_COLLECTION, ': ', e

        print "Restoring eXist Root Collection: %s" % _stored_default_collection
        settings.EXISTDB_ROOT_COLLECTION = _stored_default_collection


starting_tests.connect(_use_test_collection)
finished_tests.connect(_restore_root_collection)
