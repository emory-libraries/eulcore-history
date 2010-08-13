# file django/existdb/management/commands/existdb_index.py
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

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from eulcore.django.existdb import ExistDB

class Command(BaseCommand):    
    help = """Tasks for managing eXist-db index configuration file.

Available subcommands:
  load      - load index configuration file to eXist
  show      - show the contents of index configuration file currently in eXist
  show-info - show information about index configuration file in eXist (owner, date modified, etc.)
  remove    - remove index configuration from eXist
            """
    args = 'load | show | show-info | remove'
    
    def handle(self, *args, **options):
        if not len(args) or args[0] == 'help':
            print self.help
            return

        cmd = args[0]
        if cmd not in ['load', 'show', 'show-info', 'remove']:
            print "Command '%s' not recognized" % cmd
            print self.help
            return

        # check for required settings (used in all modes)
        if not hasattr(settings, 'EXISTDB_ROOT_COLLECTION') or not settings.EXISTDB_ROOT_COLLECTION:
            raise CommandError("EXISTDB_ROOT_COLLECTION setting is missing")
            return
        if not hasattr(settings, 'EXISTDB_INDEX_CONFIGFILE') or not settings.EXISTDB_INDEX_CONFIGFILE:
            raise CommandError("EXISTDB_INDEX_CONFIGFILE setting is missing")
            return

        collection = settings.EXISTDB_ROOT_COLLECTION
        index = settings.EXISTDB_INDEX_CONFIGFILE

        try:
            self.db = ExistDB()

            # check there is already an index config
            hasindex = self.db.hasCollectionIndex(collection)

            # for all commands but load, nothing to do if config collection does not exist
            if not hasindex and cmd != 'load':
                print "Collection %s has no index configuration" % collection
                return

            if cmd == 'load':
                # load collection index to eXist

                # no easy way to check if index is different, but give some info to user to help indicate
                if hasindex:
                    index_desc = self.db.describeDocument(self.db._collectionIndexPath(collection))
                    print "Collection already has an index configuration; last modified %s\n" % index_desc['modified']
                else:
                    print "This appears to be a new index configuration\n"

                message =  "eXist index configuration \n collection:\t%s\n index file:\t%s" % (collection, index)

                success = self.db.loadCollectionIndex(collection, open(index))
                if success:
                    print "Succesfully updated %s" % message
                    print """
If your collection already contains data and the index configuration
is new or has changed, you should reindex the collection.
            """
                else:
                    raise CommandError("Failed to update %s" % message)

            elif cmd == 'show':
                # show the contents of the the collection index config file in exist
                print self.db.getDoc(self.db._collectionIndexPath(collection))

            elif cmd == 'show-info':
                # show information about the collection index config file in exist
                index_desc = self.db.describeDocument(self.db._collectionIndexPath(collection))
                for field, val in index_desc.items():
                    print "%s:\t%s" % (field, val)

            elif cmd == 'remove':
                # remove any collection index in eXist
                if self.db.removeCollectionIndex(collection):
                    print "Removed collection index configuration for %s" % collection
                else:
                    raise CommandError("Failed to remove collection index configuration for %s" % collection)

        except Exception, err:
            # better error messages would be nice...
            raise CommandError(err)

