"""Functions and classes for parsing XPath expressions into abstract syntax
trees and serializing them back to strings.

This module exports two key functions, :func:`parse` and :func:`serialize`.

.. function:: parse(xpath_str)

   Parse a string XPath expression into an abstract syntax tree. The AST
   will be built from the classes defined in :mod:`eulcore.xpath.ast`.

.. function:: serialize(xpath_ast)

   Serialize an XPath AST expressed in terms of :mod:`eulcore.xpath.ast`
   objects into a valid XPath string.

This module does not support evaluating XPath expressions.
"""

from eulcore.xpath.core import parse, serialize
