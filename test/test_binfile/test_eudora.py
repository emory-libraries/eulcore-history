#!/usr/bin/env python

import unittest
import os

from eulcommon.binfile import eudora
from testcore import main

TEST_ROOT = os.path.dirname(__file__)
def fixture(fname):
    return os.path.join(TEST_ROOT, 'fixtures', fname)

class TestEudora(unittest.TestCase):
    def test_members(self):
        fname = fixture('In.toc')
        obj = eudora.Toc(fname)

        self.assertEqual(obj.version, 1)
        self.assertEqual(obj.name, 'In')
        
        messages = list(obj.messages)
        self.assertEqual(len(messages), 2)

        # note: we don't actually test all of the fields here. it's not
        # clear what a few of them actually are, so we only test the ones we
        # know how to interpret.

        self.assertTrue(isinstance(messages[0], eudora.Message))
        self.assertEqual(messages[0].offset, 0)
        self.assertEqual(messages[0].size, 1732)
        self.assertEqual(messages[0].body_offset, 955)
        self.assertEqual(messages[0].to, 'Somebody ')
        self.assertEqual(messages[0].subject, 'Welcome')

        # second message isn't *necessarily* immediately after first, but
        # in this case it is.
        self.assertEqual(messages[1].offset, 1732)


if __name__ == '__main__':
    main()
