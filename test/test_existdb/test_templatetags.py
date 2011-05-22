#!/usr/bin/env python

from lxml import etree
import unittest

from eulexistdb.db import EXISTDB_NAMESPACE
from eulexistdb.templatetags.existdb import exist_matches
from eulxml.xmlmap import XmlObject

from testcore import main

class ExistMatchTestCase(unittest.TestCase):
# test exist_match template tag explicitly
    SINGLE_MATCH = """<abstract>Pitts v. <exist:match xmlns:exist="%s">Freeman</exist:match>
school desegregation case files</abstract>""" % EXISTDB_NAMESPACE
    MULTI_MATCH = """<title>Pitts v. <exist:match xmlns:exist="%(ex)s">Freeman</exist:match>
<exist:match xmlns:exist="%(ex)s">school</exist:match> <exist:match xmlns:exist="%(ex)s">desegregation</exist:match>
case files</title>""" % {'ex': EXISTDB_NAMESPACE}

    def setUp(self):
        self.content = XmlObject(etree.fromstring(self.SINGLE_MATCH))   # placeholder

    def test_single_match(self):
        self.content.node = etree.fromstring(self.SINGLE_MATCH)
        format = exist_matches(self.content)
        self.assert_('Pitts v. <span class="exist-match">Freeman</span>'
            in format, 'exist:match tag converted to span for highlighting')

    def test_multiple_matches(self):
        self.content.node = etree.fromstring(self.MULTI_MATCH)
        format = exist_matches(self.content)
        self.assert_('Pitts v. <span class="exist-match">Freeman</span>'
            in format, 'first exist:match tag converted')
        self.assert_('<span class="exist-match">school</span> <span class="exist-match">desegregation</span>'
            in format, 'second and third exist:match tags converted')



if __name__ == '__main__':
    main()
