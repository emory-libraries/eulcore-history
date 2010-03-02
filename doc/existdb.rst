:mod:`eulcore.existdb` -- Store and retrieve data in an eXist database
======================================================================

.. automodule:: eulcore.existdb

.. FIXME: automodules here rely on undoc-members to include undocumented
     members in the output documentation. We should move away from this,
     preferring instead to add docstrings and/or reST docs right here) for
     members that need documentation.

Direct database access
----------------------

.. automodule:: eulcore.existdb.db

   .. autoclass:: ExistDB(server_url[, resultType[, encoding[, verbose]]])
      :members:
      :undoc-members:

   .. autoclass:: QueryResult
      :members:
      :undoc-members:

   .. autoexception:: ExistDBException


Model-based access
-----------------------------

.. automodule:: eulcore.existdb.query
   :members:
   :undoc-members:

:mod:`eulcore.django.existdb` -- Django tie-ins
-----------------------------------------------

.. include:: ../src/eulcore/django/existdb/README

.. automodule:: eulcore.django.existdb
   :members:
   :undoc-members:

.. automodule:: eulcore.django.existdb.db
   :members:
   :undoc-members:
