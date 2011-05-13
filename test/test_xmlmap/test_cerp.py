#!/usr/bin/env python

import unittest
import os

from eulxml.xmlmap import cerp, load_xmlobject_from_file
from testcore import main

class TestCerp(unittest.TestCase):
    FIXTURE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'fixtures', 'In.cerp')

    def setUp(self):
        self.account = load_xmlobject_from_file(self.FIXTURE_FILE, cerp.Account)
        self.folder = self.account.folders[0]
        self.message = self.folder.messages[0]

    def testAccount(self):
        self.assertTrue(isinstance(self.account, cerp.Account))
        self.assertEqual(len(self.account.folders), 1)

    def testFolder(self):
        self.assertTrue(isinstance(self.folder, cerp.Folder))
        self.assertEqual(self.folder.name, 'In')
        self.assertEqual(len(self.folder.messages), 1)

    def testMessage(self):
        self.assertTrue(isinstance(self.message, cerp.Message))
        self.assertEqual(self.message.local_id, 3)
        self.assertEqual(self.message.message_id,
                '<960XXXX01955_100560.XXXX_EHK76-1@CompuServe.COM>')
        self.assertEqual(self.message.orig_date_list,
                ['1996-07-24T06:19:55-04:00'])
        self.assertEqual(self.message.from_list,
                ['Somebody <somebody@CompuServe.COM>'])
        self.assertEqual(self.message.to_list,
                ['Somebody Else <somebody@example.com>'])
        self.assertEqual(self.message.subject_list,
                ['various'])

        expect_header_names = [ 'Received', 'Date', 'From', 'To', 'Subject',
                                'Message-Id', 'Status' ]
        actual_header_names = [ h.name for h in self.message.headers ]
        self.assertEqual(actual_header_names, expect_header_names)

        self.assertEqual(self.message.eol, 'LF')

if __name__ == '__main__':
    main()
