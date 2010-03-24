from django.conf import settings
from eulcore.django.existdb.db import ExistDB
from eulcore.existdb.query import QuerySet

class Manager(object):
    def __init__(self, xpath):
        self.xpath = xpath

        # NOTE: model needs to be patched in to a real XmlModel class after
        # the fact. currently this is handled by XmlModelType metaclass
        # logic.
        self.model = None

    def get_query_set(self):
        return QuerySet(model=self.model, xpath=self.xpath, using=ExistDB(),
                        collection=settings.EXISTDB_ROOT_COLLECTION)

    #######################
    # PROXIES TO QUERYSET #
    #######################

    def count(self):
        return self.get_query_set().count()

    def filter(self, *args, **kwargs):
        return self.get_query_set().filter(*args, **kwargs)

    def order_by(self, *args, **kwargs):
        return self.get_query_set().order_by(*args, **kwargs)

    def only(self, *args, **kwargs):
        return self.get_query_set().only(*args, **kwargs)

    def also(self, *args, **kwargs):
        return self.get_query_set().also(*args, **kwargs)

    def distinct(self):
        return self.get_query_set().distinct(*args, **kwargs)

    def all(self):
        return self.get_query_set().all()

    def get(self, *args, **kwargs):
        return self.get_query_set().get(*args, **kwargs)

