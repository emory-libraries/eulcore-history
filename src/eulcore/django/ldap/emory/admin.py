from django.contrib import admin
from eulcore.django.ldap.emory.models import EmoryLDAPUser

admin.site.register(EmoryLDAPUser)
