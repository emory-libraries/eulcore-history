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

    print "Creating eXist Test Collection: %s" % (settings.EXISTDB_ROOT_COLLECTION,)
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
        print "Removing eXist Test Collection: %s" % (settings.EXISTDB_ROOT_COLLECTION,)
        # before restoring existdb non-test root collection, init db connection
        db = ExistDB()
        try:            
            # remove test collection
            db.removeCollection(settings.EXISTDB_ROOT_COLLECTION)
        except ExistDBException, e:
            print "Error removing collection " + settings.EXISTDB_ROOT_COLLECTION + e.message

        print "Restoring eXist Root Collection: %s" % (_stored_default_collection,)
        settings.EXISTDB_ROOT_COLLECTION = _stored_default_collection


starting_tests.connect(_use_test_collection)
finished_tests.connect(_restore_root_collection)
