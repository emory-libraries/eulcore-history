# file django\fedora\server.py
# 
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

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

        if hasattr(settings, 'FEDORA_PIDSPACE'):
            self.default_pidspace = settings.FEDORA_PIDSPACE

