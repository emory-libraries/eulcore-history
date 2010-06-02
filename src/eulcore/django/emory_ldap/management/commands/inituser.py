# New Manage.py comman to init users from the LDAP.
# See Django documentation on using additional manage.py commands
# In brief however this will appear in the list of commands returned
# by 'manage.py help' with help text as to how to execute.

from django.core.management.base import BaseCommand
from eulcore.django.emory_ldap.backends import EmoryLDAPBackend

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
