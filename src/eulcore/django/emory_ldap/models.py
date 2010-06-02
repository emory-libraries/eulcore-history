from django.contrib.auth.models import User
from django.db import models

class EmoryLDAPUser(User):
    phone = models.CharField(max_length=50, blank=True)
    dept_num = models.CharField(max_length=50, blank=True)
    full_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=100, blank=True)
    employee_num = models.CharField(max_length=50, blank=True)
    subdept_code = models.CharField(max_length=50, blank=True)
    hr_id = models.CharField(max_length=50, blank=True)

    def get_full_name(self):
        super_full = super(EmoryLDAPUser, self).get_full_name
        return self.full_name or super_full()
