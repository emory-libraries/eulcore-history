:mod:`eulcore.xpath` -- Parse and Serialize XPath
=================================================

.. automodule:: eulcore.xpath

:mod:`eulcore.xpath.ast` -- Abstract syntax trees for XPath
-----------------------------------------------------------
.. automodule:: eulcore.xpath.ast
   :members:


Notes
-----

 * The :mod:`re` standard library module in Python had a bug prior to 2.6.4 that
   made it reject characters with Unicode characters above U+FFFF. As a result,
   XPath expressions including these characters in node names, namespace
   abbreviations, or function names will not work correctly in those versions of
   Python.

   If you don't know what this means you, almost certainly don't need to worry
   about it.