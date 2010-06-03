from django.contrib import admin
from eulcore.django.emory_ldap.models import EmoryLDAPUser

admin.site.register(EmoryLDAPUser)
