from django.core.management.base import BaseCommand
from eulcore.django.fedora import Repository
from eulcore.fedora import DigitalObject
from eulcore.fedora.models import ContentModel

class Command(BaseCommand):
    help = """Generate missing Fedora content model objects."""

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.repo = Repository()

    def handle(self, *args, **options):
        for name, cls in DigitalObject.defined_types.iteritems():
            self.process_class(cls)

    def process_class(self, cls):
        try:
            ContentModel.for_class(cls, self.repo)
        except ValueError:
            # for_class raises a ValueError when a class has >1
            # CONTENT_MODELS.
            pass
