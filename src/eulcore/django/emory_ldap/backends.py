# file django/emory_ldap/backends.py
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

from eulcore.django.ldap.backends import LDAPBackend, map_fields
from eulcore.django.emory_ldap.models import EmoryLDAPUserProfile

class EmoryLDAPBackend(LDAPBackend):
    def update_user_fields(self, user, extra_fields):
        super(EmoryLDAPBackend, self).update_user_fields(user, extra_fields)
        user.is_staff = True

    def update_user_profile_fields(self, profile, extra_fields):
        super(EmoryLDAPBackend, self).update_user_profile_fields(profile, extra_fields)
        map_fields(profile, extra_fields,
            phone='telephoneNumber',
            dept_num='departmentNumber',
            full_name='cn',
            title='title',
            employee_num='employeeNumber',
            subdept_code='emorysubdeptcode',
            hr_id='hremplid')