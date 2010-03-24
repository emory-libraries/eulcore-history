"""Map XML to Python objects.

This package facilitates access to XML data using common Pythonic idioms. XML
nodes map to Python attributes using XPath expressions.

For developer convenience this package is divided into submodules. Users
should import the names directly from eulcore.xmlmap. This package exports
the following names:
 * XmlObject -- a base class for XML-Python mapping objects
 * parseUri and parseString -- parse a URI or string into a DOM node with
   XPath methods that xmlmap depends on
 * load_xmlobject_from_string and load_xmlobject_from_file -- parse a string
   or file directly into an XmlObject
 * NodeField and NodeListField -- field classes for mapping relative
   DOM nodes to other XmlObjects
 * StringField and StringListField -- field classes for mapping DOM
   nodes to Python strings
 * IntegerField and IntegerListField -- field classes for mapping DOM
   nodes to Python integers

"""


from eulcore.xmlmap.core import *
from eulcore.xmlmap.descriptor import *
from eulcore.xmlmap.fields import *
