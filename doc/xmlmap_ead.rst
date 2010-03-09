:mod:`eulcore.xmlmap.eadmap` - Encoded Archival Description (EAD)
=================================================================

.. module:: eulcore.xmlmap.eadmap

General Information
-------------------
The Encoded Archival Description (EAD) is a a standard xml format for encoding
finding aids.  For more information, please consult `the official Library of
Congress EAD site <http://www.loc.gov/ead/>`_.

This set of xml objects is an attempt to make the major fields of an EAD document
accessible for search and display.  It is by no means an exhaustive mapping of all
EAD elements in all their possible configurations.

Encoded Archival Description
----------------------------

Nearly all fields in all EAD XmlObjects are mapped as
:class:`eulcore.xmlmap.XPathString` or :class:`eulcore.xmlmap.XPathStringList`,
except for custom EAD sub-objects, which are indicated where in use.

  .. autoclass:: eulcore.xmlmap.eadmap.EncodedArchivalDescription(dom_node[, context])
      :members:

Archival Description
--------------------

  .. autoclass:: eulcore.xmlmap.eadmap.ArchivalDescription(dom_node[, context])
      :members:

Subordinate Components
----------------------

  .. autoclass:: eulcore.xmlmap.eadmap.SubordinateComponents(dom_node[, context])
      :members:

  .. autoclass:: eulcore.xmlmap.eadmap.Component(dom_node[, context])
      :members:

Controlled Access Headings
--------------------------

  .. autoclass:: eulcore.xmlmap.eadmap.ControlledAccessHeadings(dom_node[, context])
      :members:

  .. autoclass:: eulcore.xmlmap.eadmap.Heading(dom_node[, context])
      :members:


Miscellaneous
-------------

  .. autoclass:: eulcore.xmlmap.eadmap.DescriptiveIdentification(dom_node[, context])
      :members:

  .. autoclass:: eulcore.xmlmap.eadmap.Container(dom_node[, context])
      :members:
      
  .. autoclass:: eulcore.xmlmap.eadmap.Section(dom_node[, context])
      :members:

  
