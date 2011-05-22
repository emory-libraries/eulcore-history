#!/usr/bin/env python

import os
import unittest

from django.conf import settings

from eulxml import xmlmap
from eulexistdb.db import ExistDB
from eulexistdb.manager import Manager
from eulexistdb.models import XmlModel

from testcore import main


# test model/manager logic

class PartingBase(xmlmap.XmlObject):
    '''A plain XmlObject comparable to how one might be defined in
    production code.'''
    exclamation = xmlmap.StringField('exclamation')
    target = xmlmap.StringField('target')

class Parting(XmlModel, PartingBase):
    '''An XmlModel can derive from an XmlObject to incorporate its
    fields.'''
    objects = Manager('/parting')

class ModelTest(unittest.TestCase):
    COLLECTION = settings.EXISTDB_TEST_COLLECTION

    def setUp(self):
        self.db = ExistDB()
        self.db.createCollection(self.COLLECTION, True)

        test_dir = os.path.dirname(os.path.abspath(__file__))
        fixture = os.path.join(test_dir, 'exist_fixtures', 'goodbye-english.xml')
        loaded = self.db.load(open(fixture), self.COLLECTION + '/goodbye-english.xml', True)
        fixture = os.path.join(test_dir, 'exist_fixtures', 'goodbye-french.xml')
        loaded = self.db.load(open(fixture), self.COLLECTION + '/goodbye-french.xml', True)

        # temporarily set test collection as root exist collection
        self._root_collection = settings.EXISTDB_ROOT_COLLECTION
        settings.EXISTDB_ROOT_COLLECTION = self.COLLECTION

    def tearDown(self):
        self.db.removeCollection(self.COLLECTION)

        settings.EXISTDB_ROOT_COLLECTION = self._root_collection

    def test_manager(self):
        partings = Parting.objects.all()
        self.assertEquals(2, partings.count())


if __name__ == '__main__':
    main()
