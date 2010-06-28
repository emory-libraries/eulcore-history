import re
from glob import glob
from os import path
from django.test import TestCase as DjangoTestCase
from django.conf import settings
from eulcore.django.existdb.db import ExistDB, ExistDBException

class TestCase(DjangoTestCase):
    """Customization of :class:`django.test.TestCase`

    If TestCase instance has an attribute named ``exist_fixtures``, the
    specified fixtures will be loaded to eXist before the tests run.
    
    The ``exist_fixtures`` attribute should be a dictionary with information
    about fixtures to load to eXist. Currently supported options:

    * *index* - path to an eXist index configuration file; will be loaded before
      any other fixture files, and removed in fixture teardown
    * *directory* - path to a fixture directory; all .xml files in the directory
      will be loaded to eXist
    * *files* - list of files to be loaded (filenames should include path)

    """

    def assertPattern(self, regex, text, msg_prefix=''):
        """Assert that a string matches a regular expression (regex compiled as multiline).
           Allows for more flexible matching than the django assertContains.
         """
        if msg_prefix != '':
            msg_prefix += '.  '
        self.assert_(re.search(re.compile(regex, re.DOTALL), text),
        msg_prefix + "Should match '%s'" % regex)

    def _fixture_setup(self):
        if hasattr(self, 'exist_fixtures'):
            db = ExistDB()
            # load index
            if 'index' in self.exist_fixtures:
                db.loadCollectionIndex(settings.EXISTDB_ROOT_COLLECTION,
                        open(self.exist_fixtures['index']))
            if 'directory' in self.exist_fixtures:
                for file in glob(path.join(self.exist_fixtures['directory'], '*.xml')):
                    self._load_file_to_exist(file)
            if 'files' in self.exist_fixtures:
                for file in self.exist_fixtures['files']:
                    self._load_file_to_exist(file)

        return super(TestCase, self)._fixture_setup()

    def _fixture_teardown(self):
        if hasattr(self, 'exist_fixtures'):
            db = ExistDB()
            if 'index' in self.exist_fixtures:
                db.removeCollectionIndex(settings.EXISTDB_ROOT_COLLECTION)
            if 'directory' in self.exist_fixtures:
                for file in glob(path.join(self.exist_fixtures['directory'], '*.xml')):
                    self._remove_file_from_exist(file)
            if 'files' in self.exist_fixtures:
                for file in self.exist_fixtures['files']:
                    self._remove_file_from_exist(file)

        return super(TestCase, self)._fixture_teardown()

    def _load_file_to_exist(self, file):
        db = ExistDB()
        fname = path.split(file)[-1]
        exist_path= path.join(settings.EXISTDB_ROOT_COLLECTION, fname)
        db.load(open(file), exist_path, True)

    def _remove_file_from_exist(self, file):
        db = ExistDB()
        fname = path.split(file)[-1]
        exist_path= path.join(settings.EXISTDB_ROOT_COLLECTION, fname)
        # tests could remove fixtures, so an exception here is not a problem
        try:
            db.removeDocument(exist_path)
        except ExistDBException, e:
            # any way to determine if error ever needs to be reported?
            pass
