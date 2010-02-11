# import core xmlmap components so they can be used as eulcore.xmlmap
from eulcore.xmlmap.core import XmlObject, parseUri, parseString
from eulcore.xmlmap.core import load_xmlobject_from_string, load_xmlobject_from_file

from eulcore.xmlmap.descriptor import XPathDate, XPathDateList
from eulcore.xmlmap.descriptor import XPathInteger, XPathIntegerList
from eulcore.xmlmap.descriptor import XPathNode, XPathNodeList
from eulcore.xmlmap.descriptor import XPathString, XPathStringList
