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

    def get_full_name(self):
        return self.full_name or self.user.get_full_name()

def _create_profile(sender, instance, created, **kwargs):
    if created:
        profile = EmoryLDAPUserProfile(user=instance)
        profile.save()
post_save.connect(_create_profile, sender=User)
