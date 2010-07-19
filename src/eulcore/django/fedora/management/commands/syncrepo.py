from django.core.management.base import BaseCommand
from eulcore.fedora import DigitalObject

class Command(BaseCommand):
    help = """Generate missing Fedora content model objects."""

    def handle(self, *args, **options):
        for name, cls in DigitalObject.defined_types.iteritems():
            self.process_class(name, cls)

    def process_class(self, name, cls):
        cmodels = cls.CONTENT_MODELS
        if not cmodels:
            return
        if len(cmodels) > 1:
            print >>sys.stderr, ('%s has %d content models, but syncrepo ' +
                   'supports only one per class. Skipping class.' %
                     (name, len(cmodels)))
            return
    
        cmodel_uri = cmodels[0]
        # cls._local_datastreams keys are python member names; values are
        # Datastream objects
        for ds in cls._local_datastreams.values():
            # TODO: ...
            pass
