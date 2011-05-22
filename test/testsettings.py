import os

# test secret key for eulfedora.cryptutil tests
SECRET_KEY = 'abcdefghijklmnopqrstuvwxyz1234567890'


INSTALLED_APPS = (
    'eulfedora',
)


FEDORA_FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   'test_fedora', 'fixtures')

from localsettings import *
