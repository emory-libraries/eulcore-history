:mod:`eulcore.existdb` -- Store and retrieve data in an eXist database
======================================================================

.. automodule:: eulcore.existdb

.. FIXME: automodules here rely on undoc-members to include undocumented
     members in the output documentation. We should move away from this,
     preferring instead to add docstrings and/or reST docs right here) for
     members that need documentation.

See :mod:`eulcore.django.existdb` for existdb and django integration.

Direct database access
----------------------

.. automodule:: eulcore.existdb.db

   .. autoclass:: ExistDB(server_url[, resultType[, encoding[, verbose]]])

      .. automethod:: getDoc(name)

      .. automethod:: createCollection(collection_name[, overwrite])

      .. automethod:: removeCollection(collection_name)

      .. automethod:: hasCollection(collection_name)

      .. automethod:: load(xml, path[, overwrite])

      .. automethod:: query(xquery[, start[, how_many]])

      .. automethod:: executeQuery(xquery)

      .. automethod:: querySummary(result_id)

      .. automethod:: getHits(result_id)

      .. automethod:: retrieve(result_id, position)

      .. automethod:: releaseQueryResult(result_id)

   .. autoclass:: QueryResult
      :members:

   .. autoexception:: ExistDBException


Model-based access
-----------------------------

.. automodule:: eulcore.existdb.query

   .. autoclass:: QuerySet
      :members:


