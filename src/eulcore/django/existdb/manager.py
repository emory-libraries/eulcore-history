# file django/existdb/manager.py
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

from django.conf import settings
from eulcore.django.existdb.db import ExistDB
from eulcore.existdb.query import QuerySet

class Manager(object):

    """
    Connect an :class:`~eulcore.django.existdb.models.XmlModel` to an
    :class:`~eulcore.django.existdb.db.ExistDB` for easy querying.
    
    Typically each :class:`~eulcore.django.existdb.models.XmlModel` will
    have one or more ``Manager`` members. Like Django ``Manager`` objects
    these offer a convenient way to access model-based queries. Like Django
    ``Manager`` objects, developers can `derive a child class`_ and override
    :meth:`get_query_set` to modify the default ``QuerySet``. Unlike Django,
    this implementation does not currently provide a default ``Manager`` for
    every ``XmlModel``.

    Developers should consult :class:`eulcore.existdb.query.QuerySet` for a
    complete list of its methods. ``Manager`` directly exposes these
    methods, forwarding them to the ``QuerySet`` returned by its own
    :meth:`get_query_set`.

    .. _derive a child class: http://docs.djangoproject.com/en/1.1/topics/db/managers/#modifying-initial-manager-querysets
    """

    def __init__(self, xpath):
        self.xpath = xpath

        # NOTE: model needs to be patched in to a real XmlModel class after
        # the fact. currently this is handled by XmlModelType metaclass
        # logic.
        self.model = None

    def get_query_set(self):
        """
        Get the default :class:`eulcore.django.existdb.db.QuerySet` returned
        by this ``Manager``. Typically this returns a ``QuerySet`` based on
        the ``Manager``'s `xpath`, evaluated in the
        ``settings.EXISTDB_ROOT_COLLECTION`` on a default
        :class:`eulcore.django.existdb.db.ExistDB`.

        This is a convenient point for developers to customize an object's
        managers. Deriving a child class from Manager and overriding or
        extending this method is a handy way to create custom queries
        accessible from an :class:`~eulcore.django.existdb.models.XmlModel`.
        """

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

