:mod:`eulcore.xmlmap` -- Map XML to Python objects
==================================================

.. module:: eulcore.xmlmap

:mod:`eulcore.xmlmap` makes it easier to map XML to Python objects. The
Python DOM does some of this, of course, but sometimes it's prettier to wrap
a DOM node in a typed Python object and assign attributes on that object to
reference subnodes by XPath_ expressions. This module provides that
functionality for read-only attributes, and in the future it aims to allow
setting them as well.

.. _XPath: http://www.w3.org/TR/xpath/

General Usage
-------------

Let's say we have an XML object that looks something like this:

.. code-block:: xml

   <foo>
     <bar>
       <baz>42</baz>
     </bar>
     <bar>
       <baz>13</baz>
     </bar>
   </foo>

For this example, we want to access the value of the first ``<baz>`` as a
Python integer and the second ``<baz>`` as a string value. We also want to
access all of them (there may be lots on another ``<foo>``) as a big list of
integers. We can create an object to map these fields like this::

   from eulcore import xmlmap

   class Foo(xmlmap.XmlObject):
       first_baz = xmlmap.XPathInteger('bar[1]/baz')
       second_baz = xmlmap.XPathString('bar[2]/baz')
       all_baz = xmlmap.XPathIntegerList('bar/baz')
   
:attr:`first_baz`, :attr:`second_baz`, and :attr:`all_baz` here are
attributes of the :class:`Foo` object. We can access them in later code like
this::

  >>> foo = xmlmap.load_xmlobject_from_file(foo_path, xmlclass=Foo)
  >>> foo.first_baz
  42
  >>> foo.second_baz
  u'13'
  >>> foo.all_baz
  [42, 13]


API
---

.. FIXME: automodules here rely on undoc-members to include undocumented
     members in the output documentation. We should move away from this,
     preferring instead to add docstrings and/or reST docs right here) for
     members that need documentation.

.. automodule:: eulcore.xmlmap.core
   :members:
   :undoc-members:

.. automodule:: eulcore.xmlmap.descriptor
   :members:
   :undoc-members:
