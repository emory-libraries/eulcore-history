# file eulocal/django/emory_ldap/admin.py
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

from django.core.urlresolvers import reverse
from django.contrib import admin
from eullocal.django.emory_ldap.models import EmoryLDAPUserProfile

class EmoryLDAPUserProfileAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'full_name', 'edit_user')

    def edit_user(self, profile):
        href = reverse('admin:auth_user_change', args=(profile.user.id,))
        return 'User <a href="%s">%s</a>' % (href, profile.user.username)
    edit_user.allow_tags = True

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        base_urls = super(EmoryLDAPUserProfileAdmin, self).get_urls()
        my_urls = patterns('eullocal.django.emory_ldap.views',
            url(r'add-username/', 'add_username', name='add_username'),
        )
        return my_urls + base_urls

admin.site.register(EmoryLDAPUserProfile, EmoryLDAPUserProfileAdmin)
