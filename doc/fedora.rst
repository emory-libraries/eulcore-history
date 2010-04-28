:mod:`eulcore.fedora` -- Python objects to interact with the Fedora Commons repository
======================================================================================

.. module:: eulcore.fedora

:mod:`eulcore.fedora` attemps to provide a pythonic interface to the
`Fedora Commons repository <http://fedora-commons.org/confluence/display/FCR30>`_.

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

API Wrappers
^^^^^^^^^^^^

.. autoclass:: REST_API
    :members:

.. autoclass:: API_A_LITE
    :members:

.. autoclass:: API_M
    :members:

Utility functions
^^^^^^^^^^^^^^^^^

.. automethod:: eulcore.fedora.server.read_uri

.. automethod:: eulcore.fedora.server.auth_headers

.. automethod:: eulcore.fedora.server.parse_rdf

.. automethod:: eulcore.fedora.server.parse_xml_object