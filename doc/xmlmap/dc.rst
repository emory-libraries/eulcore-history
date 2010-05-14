:mod:`eulcore.xmlmap.dc` - Dublin Core
======================================

.. module:: eulcore.xmlmap.dc

General Information
-------------------
  Thorough documentation of Dublin Core and all the elements included in simple,
  unqaulified DC is available from the Dublin Core Metadata Initiative.  In particular, see
  `Dublin Core Metadata Element Set, Version 1.1 <http://dublincore.org/documents/dces/>`_.

Dublin Core
-----------

All elements in Dublin Core are optional and can be repeated, so each field has
been mapped as a single element (:class:`eulcore.xmlmap.StringField`) and as a list
(:class:`eulcore.xmlmap.StringListField`), named according to the DC element.

Because the DC elements are thoroughly and clearly documented at http://dublincore.org,
element descriptions have not been repeated here.

  .. autoclass:: eulcore.xmlmap.dc.DublinCore([dom_node[, context]])
    :members:
    :undoc-members:
