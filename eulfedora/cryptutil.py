from Crypto.Cipher import Blowfish as EncryptionAlgorithm
import hashlib
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# NOTE: current encryption logic should be easily adapted to most of the
# encryption algorithms supported by Crypto that allow for variable key length

ENCRYPTION_KEY = None
ENCRYPT_PAD_CHARACTER = '\0'

def _get_encryption_key():
    '''Method for accessing an encryption key based on the SECRET_KEY
    defined in django settings.'''
    # initialize ENCRYPTION_KEY the first time it is needed, so that
    # applications that use eulcore without using this specific
    # functionality do not get bogus warnings about SECRET_KEY size.

    global ENCRYPTION_KEY
    global ENCRYPT_PAD_CHARACTER
    if ENCRYPTION_KEY is None:
        # NOTE: Blowfish key length is variable but must be 32-448 bits
        # (but PyCrypto does not actually make this information accessible)
        KEY_MIN_CHARS = 32/8
        KEY_MAX_CHARS = 448/8
        if KEY_MIN_CHARS <= len(settings.SECRET_KEY) <= KEY_MAX_CHARS:
            ENCRYPTION_KEY = settings.SECRET_KEY
        else:
            ENCRYPTION_KEY = hashlib.sha224(settings.SECRET_KEY).hexdigest()
            message = '''Django secret key (current length of %d) requires hashing for use as encryption key
            (to avoid hashing, should be %d-%d characters)''' % \
            (len(settings.SECRET_KEY), KEY_MIN_CHARS, KEY_MAX_CHARS)
            logger.warn(message)
    return ENCRYPTION_KEY

def encrypt(text):
    'Encrypt a string using an encryption key based on the django SECRET_KEY'
    crypt = EncryptionAlgorithm.new(_get_encryption_key())
    return crypt.encrypt(to_blocksize(text))

def decrypt(text):
    'Decrypt a string using an encryption key based on the django SECRET_KEY'
    crypt = EncryptionAlgorithm.new(_get_encryption_key())
    return crypt.decrypt(text).rstrip(ENCRYPT_PAD_CHARACTER)

def to_blocksize(password):
    # pad the text to create a string of acceptable block size for the encryption algorithm
    width = len(password) + \
        (EncryptionAlgorithm.block_size - len(password) % EncryptionAlgorithm.block_size)
    block = password.ljust(width, ENCRYPT_PAD_CHARACTER)
    return block

