# file django/existdb/management/commands/existdb_reindex.py
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

        # Explicitly request no timeout (even if one is configured in
        # django settings), since reindexing could take a while.
        self.db = ExistDB(timeout=None)
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
