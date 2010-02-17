from eulcore.django.testsetup import starting_tests, finished_tests
from django.conf import settings

_stored_default_collection = None

def use_test_collection(sender, **kwargs):    
    global _stored_default_collection
    _stored_default_collection = getattr(settings, "EXISTDB_ROOT_COLLECTION", None)

    if getattr(settings, "EXISTDB_TEST_COLLECTION", None):
        settings.EXISTDB_ROOT_COLLECTION = settings.EXISTDB_TEST_COLLECTION
    else:
        settings.EXISTDB_ROOT_COLLECTION = getattr(settings, "EXISTDB_ROOT_COLLECTION", "/default") + "_test"

    print "Setting eXist Test Collection: %s" % (settings.EXISTDB_ROOT_COLLECTION,)

def restore_root_collection(sender, **kwargs):
    global _stored_default_collection
    # if use_test_collection didn't run, don't change anything
    if _stored_default_collection is None:
        print "eXist test-start handler does not appear to have run; not restoring eXist Root Collection"
        print "Is 'eulcore.django.existdb' in your installed apps?"
    else:
        print "Restoring eXist Root Collection: %s" % (_stored_default_collection,)
        settings.EXISTDB_ROOT_COLLECTION = _stored_default_collection


starting_tests.connect(use_test_collection)
finished_tests.connect(restore_root_collection)
