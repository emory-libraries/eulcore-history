# New Manage.py comman to init users from the LDAP.
# See Django documentation on using additional manage.py commands
# In brief however this will appear in the list of commands returned
# by 'manage.py help' with help text as to how to execute.

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Initializes user accounts based on Emory LDAP usernames'
    args = 'username [username ...]'

    def handle(self, *usernames, **options):
        from eulcore.django.ldap.emory import EmoryLDAPServer

        els = EmoryLDAPServer()
        for uname in usernames:
            usr = els.find_user(uname)
            if usr[0]: # if user is in the system it comes back.
                print 'Initialized account for user %s' % usr[1]
            else: # If user not in system, comes back Non.
                print 'No user found for %s!!' % uname