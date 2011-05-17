# file eullocal/django/emory_ldap/management/commands/inituser.py
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

# New Manage.py comman to init users from the LDAP.
# See Django documentation on using additional manage.py commands
# In brief however this will appear in the list of commands returned
# by 'manage.py help' with help text as to how to execute.

from django.core.management.base import BaseCommand
from eullocal.django.emory_ldap.backends import EmoryLDAPBackend

class Command(BaseCommand):
    help = 'Initializes user accounts based on Emory LDAP usernames'
    args = 'username [username ...]'

    def handle(self, *usernames, **options):
        backend = self.get_backend()
        for uname in usernames:
            user_dn, user = backend.find_user(uname)
            if user_dn: # if user is in the system it comes back.
                print 'Initialized account for user %s' % (user_dn,)
            else: # If user not in system, comes back Non.
                print 'No user found for %s!!' % (uname,)

    def get_backend(self):
        return EmoryLDAPBackend()
