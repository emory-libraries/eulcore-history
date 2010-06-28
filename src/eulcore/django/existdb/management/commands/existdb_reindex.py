import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from eulcore.django.existdb import ExistDB

class Command(BaseCommand):
    help = """Reindex the configured eXist-db collection."""

    def handle(self, *args, **options):
        # check for required settings
        if not hasattr(settings, 'EXISTDB_ROOT_COLLECTION') or not settings.EXISTDB_ROOT_COLLECTION:
            raise CommandError("EXISTDB_ROOT_COLLECTION setting is missing")
            return

        collection = settings.EXISTDB_ROOT_COLLECTION      
            
        self.db = ExistDB()
        if not self.db.hasCollection(collection):
            raise CommandError("Collection %s does not exist" % collection)

        try:
            print "Reindexing collection %s" % collection
            print "-- If you have a large collection, this may take a while."
            start_time = time.time()
            success = self.db.reindexCollection(collection)
            end_time = time.time()
            if success:
                print "Successfully reindexed collection %s" % collection
                print "Reindexing took %.2f seconds" % (end_time - start_time)
            else:
                print "Failed to reindexed collection %s" % collection
                print "-- Check that the configured exist user is in the exist DBA group."
        except Exception, err:
            raise CommandError(err)