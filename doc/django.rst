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

.. automodule:: eulcore.django.existdb.manager
   :members:

.. automodule:: eulcore.django.existdb.models

   .. autoclass:: XmlModel

      Two use cases are particularly common. First, a developer may wish to
      use an ``XmlModel`` just like an :class:`~eulcore.xmlmap.XmlObject`,
      but with the added semantics of being eXist-backed::
      
        class StoredWidget(XmlModel):
            name = StringField("name")
            quantity = IntegerField("quantity")
            top_customers = StringListField("(order[@status='active']/customer)[position()<5]/name")
            objects = Manager("//widget")

      Second, if an :class:`~eulcore.xml.XmlObject` is defined elsewhere, an
      application developer might simply expose
      :class:`~eulcore.django.existdb.db.ExistDB` backed objects::

        class StoredThingie(XmlModel, Thingie):
            objects = Manager("/thingie")

      Of course, some applications ask for mixing these two cases, extending
      an existing :class:`~eulcore.xml.XmlObject` while adding
      application-specific fields::

        class CustomThingie(XmlModel, Thingie):
            best_foobar = StringField("qux/fnord[@application='myapp']/name")
            custom_detail = IntegerField("detail/@level")
            objects = Manager("/thingie")

      In addition to the fields inherited from
      :class:`~eulcore.xmlmap.XmlObject`, ``XmlModel`` objects have one
      extra field:

      .. attribute:: _managers

         A dictionary mapping manager names to
         :class:`~eulcore.django.existdb.manager.Manager` objects. This
         dictionary includes all of the managers defined on the model
         itself, though it does not currently include managers inherited
         from the model's parents.


Management commands
^^^^^^^^^^^^^^^^^^^

The following management commands will be available when you include 
:mod:`eulcore.django.existdb` in your django ``INSTALLED_APPS`` and rely on
the existdb settings described above.

For more details on these commands, use ``manage.py <command> help``

 * **existdb_index** - update, remove, and show information about the index configuration
   for a collection index
 * **existdb_reindex** - reindex a collection index in exist


:mod:`eulcore.django.fedora` -- Django tie-ins for :mod:`eulcore.fedora`
--------------------------------------------------------------------------

.. include:: ../src/eulcore/django/fedora/README

.. automodule:: eulcore.django.fedora

.. automodule:: eulcore.django.fedora.server

   .. autoclass:: Repository


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
