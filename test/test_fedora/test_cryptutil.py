#!/usr/bin/env python

import unittest

# must be set before importing anything from django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'testsettings'

from eulfedora import cryptutil
from testcore import main

class CryptTest(unittest.TestCase):
    
    def test_to_blocksize(self):
        def test_valid_blocksize(text):
            block = cryptutil.to_blocksize(text)
            self.assertEqual(0, len(block) % cryptutil.EncryptionAlgorithm.block_size,
                '''text '%s' has correct block size for encryption algorithm''' % block)
            self.assert_(text in block, 'block-sized text contains original text')

        # test text of several sizes
        test_valid_blocksize('text')
        test_valid_blocksize('texty')
        test_valid_blocksize('textish')
        test_valid_blocksize('this is some text')
        test_valid_blocksize('this would be a really long password')
        test_valid_blocksize('can you imagine typing this every time you logged in?')

    def test_encrypt_decrypt(self):
        def test_encrypt_decrypt(text):
            encrypted = cryptutil.encrypt(text)
            self.assertNotEqual(text, encrypted,
                "encrypted text (%s) should not match original (%s)" % (encrypted, text))
            decrypted = cryptutil.decrypt(encrypted)
            self.assertEqual(text, decrypted,
                "decrypted text (%s) should match original encrypted text (%s)" % (decrypted, text))

        test_encrypt_decrypt('text')
        test_encrypt_decrypt('texty')
        test_encrypt_decrypt('textier')
        test_encrypt_decrypt('textiest')
        test_encrypt_decrypt('longish password-type text')


if __name__ == '__main__':
    main()
