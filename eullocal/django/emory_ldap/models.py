# file django/emory_ldap/models.py
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

from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db import models

class AbstractEmoryLDAPUserProfile(models.Model):
    phone = models.CharField(max_length=50, blank=True)
    dept_num = models.CharField(max_length=50, blank=True)
    full_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=100, blank=True)
    employee_num = models.CharField(max_length=50, blank=True)
    subdept_code = models.CharField(max_length=50, blank=True)
    hr_id = models.CharField(max_length=50, blank=True)

    class Meta:
        abstract = True


class EmoryLDAPUserProfile(AbstractEmoryLDAPUserProfile):
    user = models.OneToOneField(User)

    def __unicode__(self):
        return unicode(self.user)

    def get_full_name(self):
        return self.full_name or self.user.get_full_name()

def _create_profile(sender, instance, created, **kwargs):
    if created:
        profile = EmoryLDAPUserProfile(user=instance)
        profile.save()
post_save.connect(_create_profile, sender=User)
