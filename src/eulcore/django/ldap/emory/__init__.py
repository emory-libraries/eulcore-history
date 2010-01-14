from eulcore.django.ldap.auth.backends import LDAPBackend
from eulcore.django.ldap import LDAPServer

def map_fields(model, source, **kwargs):
    for model_field_name, source_field_name in kwargs.items():
        if source_field_name in source:
            values = source[source_field_name]
            if values:
                setattr(model, model_field_name, values[0])


class EmoryLDAPServer(LDAPServer):
    def update_user_fields(self, user, extra_fields):
        user.set_unusable_password()
        user.is_staff = True
        map_fields(user, extra_fields,
            first_name='givenName',
            last_name='sn',
            email='mail')

    def update_user_profile_fields(self, profile, extra_fields):
        map_fields(profile, extra_fields,
            phone='telephoneNumber',
            dept_num='departmentNumber',
            full_name='cn',
            title='title',
            employee_num='employeeNumber',
            subdept_code='emorysubdeptcode',
            hr_id='hremplid')


class EmoryLDAPBackend(LDAPBackend):
    def __init__(self):
        LDAPBackend.__init__(self, serverclass=EmoryLDAPServer)
