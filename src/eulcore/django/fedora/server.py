from django.conf import settings
from eulcore.fedora import server

class Repository(server.Repository):
    """Connect to a Fedora Repository based on configuration in ``settings.py``.

    This class is a simple wrapper to initialize :class:`eulcore.fedora.server.Repository`,
    based on Fedora connection parameters in a Django settings file.
    """
    def __init__(self):
        username = None
        password = None
        if hasattr(settings, 'FEDORA_USER'):
            username = settings.FEDORA_USER
        if hasattr(settings, 'FEDORA_PASS'):
            password = settings.FEDORA_PASS
        super(Repository, self).__init__(settings.FEDORA_ROOT, username, password)


