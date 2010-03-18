:mod:`eulcore.django` -- Extensions and additions to django
======================================================================

.. automodule:: eulcore.django


:mod:`eulcore.django.existdb` -- Django tie-ins for :mod:`eulcore.existdb`
--------------------------------------------------------------------------

.. include:: ../src/eulcore/django/existdb/README

.. automodule:: eulcore.django.existdb

.. automodule:: eulcore.django.existdb.db

   .. autoclass:: ExistDB

   .. autoclass:: ResultPaginator

management commands
^^^^^^^^^^^^^^^^^^^

The following management commands will be available when you include 
:mod:`eulcore.django.existdb` in your django installed apps.

For more details on these commands, use ``manage.py <command> help``

 * **existdb_index** - update, remove, and show information about the index configuration
   for a collection index


:mod:`eulcore.django.test` - Django test extensions
---------------------------------------------------

.. automodule:: eulcore.django.test

.. autoclass:: TestCase
        :members:

        Example use of exist fixtures.  This will load the index configuration file,
        and then load all .xml files in the specified directory to the configured
        exist test collection.
        
        .. code-block:: python
        
          class MyExistViewsTest(eulcore.django.test.TestCase):
               exist_fixtures = { 'index' : exist_index_path,
                                  'directory' : exist_fixture_path }

        Note that testing with eXist full-text indexing is significantly slower
        than without, since every time eXist loads new documents (which happens
        every setUp), they must be reindexd.
