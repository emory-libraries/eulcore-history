from eulcore.django.ldap.backends import LDAPBackend, map_fields
from eulcore.django.emory_ldap.models import EmoryLDAPUser

class EmoryLDAPBackend(LDAPBackend):
    USER_MODEL = EmoryLDAPUser

    def update_user_fields(self, user, extra_fields):
        super(EmoryLDAPBackend, self).update_user_fields(user, extra_fields)
        user.is_staff = True
        map_fields(user, extra_fields,
            phone='telephoneNumber',
            dept_num='departmentNumber',
            full_name='cn',
            title='title',
            employee_num='employeeNumber',
            subdept_code='emorysubdeptcode',
            hr_id='hremplid')
