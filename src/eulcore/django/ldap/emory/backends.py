from eulcore.django.ldap.auth.backends import LDAPBackend, map_fields
from eulcore.django.ldap.emory.models import EmoryLDAPUser

class EmoryLDAPBackend(LDAPBackend):
    USER_MODEL = EmoryLDAPUser

    def update_user_fields(self, user, extra_fields):
        super(EmoryLDAPBackend, this).update_user_fields(user, extra_fields)
        user.is_staff = True
        map_fields(user, extra_fields,
            phone='telephoneNumber',
            dept_num='departmentNumber',
            full_name='cn',
            title='title',
            employee_num='employeeNumber',
            subdept_code='emorysubdeptcode',
            hr_id='hremplid')
