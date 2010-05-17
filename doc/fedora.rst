:mod:`eulcore.fedora` -- Python objects to interact with the Fedora Commons repository
======================================================================================

.. module:: eulcore.fedora

:mod:`eulcore.fedora` attemps to provide a pythonic interface to the
`Fedora Commons repository <http://fedora-commons.org/confluence/display/FCR30>`_.

Contents
--------

.. toctree::
   :maxdepth: 1

   Object and Datastream Models <fedora/models>


Server objects
---------------

Repository & Resource Index
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. module:: eulcore.fedora.server

.. autoclass:: Repository
    :members:

.. autoclass:: ResourceIndex
    :members:

Fedora objects
^^^^^^^^^^^^^^

.. autoclass:: DigitalObject
    :members:

.. autoclass:: ObjectDatastreams
    :members:

.. autoclass:: ObjectDatastream
    :members:

.. autoclass:: SearchResults
    :members:

.. autoclass:: SearchResult
    :members:
