import glob
import os

from django.core.management.base import BaseCommand
from django.db.models import get_apps

from eulcore.django.fedora import Repository
from eulcore.fedora import DigitalObject
from eulcore.fedora.models import ContentModel
from eulcore.fedora.util import RequestFailed

class Command(BaseCommand):
    help = """Generate missing Fedora content model objects and load initial objects."""

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.repo = Repository()

    def handle(self, *args, **options):
        self.verbosity = int(options.get('verbosity', 1))

        # FIXME/TODO: add count/summary info for content models objects created ?
        if self.verbosity > 1:
            print "Generating content models for %d classes" % len(DigitalObject.defined_types)
        for cls in DigitalObject.defined_types.itervalues():
            self.process_class(cls)
            
        self.load_initial_objects()
            
    def process_class(self, cls):
        try:
            ContentModel.for_class(cls, self.repo)
        except ValueError, v:
            # for_class raises a ValueError when a class has >1
            # CONTENT_MODELS.
            if self.verbosity > 1:
                print v

    def load_initial_objects(self):
        # look for any .xml files in apps under fixtures/initial_objects
        # and attempt to load them as Fedora objects
        # NOTE! any fixtures should have pids specified, or new versions of the
        # fixture will be created every time syncrepo runs


        app_module_paths =  []
        # monkey see django code, monkey do
        for app in get_apps():
            if hasattr(app, '__path__'):
                # It's a 'models/' subpackage
                for path in app.__path__:
                    app_module_paths.append(path)
            else:
                # It's a models.py module
                app_module_paths.append(app.__file__)

        app_fixture_paths = [os.path.join(os.path.dirname(path), 
                                            'fixtures', 'initial_objects', '*.xml')
                                            for  path in app_module_paths]
        fixture_count = 0
        load_count = 0
        
        for path in app_fixture_paths:
            fixtures = glob.iglob(path)
            for f in fixtures:
                # FIXME: is there a sane, sensible way to shorten file path for error/success messages?
                fixture_count += 1
                with open(f) as fixture_data:
                    # rather than pulling PID from fixture and checking if it already exists,
                    # just ingest and catch appropriate excetions
                    try:
                        pid = self.repo.ingest(fixture_data.read(), "loaded from fixture")
                        if self.verbosity > 1:
                            print "Loaded fixture %s as %s" % (f, pid)
                        load_count += 1
                    except RequestFailed, rf:
                        if hasattr(rf, 'detail'):
                            if 'ObjectExistsException' in rf.detail:
                                if self.verbosity > 1:
                                    print "Fixture %s has already been loaded" % f
                            elif 'ObjectValidityException' in rf.detail:
                                # could also look for: fedora.server.errors.ValidationException
                                # (e.g., RELS-EXT about does not match pid)
                                print "Error: fixture %s is not a valid Repository object" % f
                            else:
                                # if there is at least a detail message, display that
                                print "Error ingesting %s: %s" % (f, rf.detail)
                        else:
                            raise rf

        # summarize what was actually done
        if self.verbosity > 0:
            if fixture_count == 0:
                print "No fixtures found"
            else:
                print "Loaded %d object(s) from %d fixture(s)" % (load_count, fixture_count)
