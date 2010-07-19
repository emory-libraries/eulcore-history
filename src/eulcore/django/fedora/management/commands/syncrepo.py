from django.core.management.base import BaseCommand
from eulcore.fedora import DigitalObject, Repository
from eulcore.fedora.models import ContentModel

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """Generate missing Fedora content model objects."""

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.repo = Repository()

    def handle(self, *args, **options):
        for name, cls in DigitalObject.defined_types.iteritems():
            self.process_class(name, cls)

    def process_class(self, name, cls):
        logger.debug('considering ' + name)

        cmodels = cls.CONTENT_MODELS
        if not cmodels:
            logger.debug(name + ' has no content models. skipping')
            return
        if len(cmodels) > 1:
            logger.debug(name + ' has multiple content models. skipping')
            return
    
        cmodel_uri = cmodels[0]
        logger.debug('using cmoodel ' + cmodel_uri)

        cmodel_obj = self.repo.get_object(cmodel_uri, type=ContentModel,
                                          create=False)
        if cmodel_obj.exists:
            logger.debug(name + ' already exists. skipping')
            return

        # otherwise the cmodel doesn't exist. let's create it.
        cmodel_obj = self.repo.get_object(cmodel_uri, type=ContentModel,
                                          create=True)
        # XXX: should this be _defined_datastreams instead?
        for ds in cls._local_datastreams.values():
            ds_composite_model = cmodel_obj.ds_composite_model.contents
            type_model = ds_composite_model.get_type_model(ds.id, create=True)
            type_model.mimetype = ds.default_mimetype
        cmodel_obj.save()
