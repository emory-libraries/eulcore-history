from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save

# The fields in an abstract model, to make it easier to create a child
# profile class. If you don't want to add anything, just use
# EmoryLDAPUserProfile.
class EmoryLDAPUserProfileBase(models.Model):
    user = models.ForeignKey(User, unique=True)
    phone = models.CharField(max_length=50, blank=True)
    dept_num = models.CharField(max_length=50, blank=True)
    full_name = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=100, blank=True)
    employee_num = models.CharField(max_length=50, blank=True)
    subdept_code = models.CharField(max_length=50, blank=True)
    hr_id = models.CharField(max_length=50, blank=True)

    def get_full_name(self):
        return self.full_name or self.user.get_full_name()

    def __unicode__(self):
        return unicode(self.user)

    class Meta:
        abstract = True


# to cache this user ldap profile information in your project database, make
# the following changes to your settings.py:
#   * add 'eulcore.ldap.emory' to your INSTALLED_APPS
#   * set AUTH_PROFILE_MODULE = 'emory.EmoryLDAPUserProfile'
class EmoryLDAPUserProfile(EmoryLDAPUserProfileBase):
    pass


def create_profile(sender, instance, created, **kwargs):
    if sender is not User:
        raise RuntimeError('create_profile() called on non-User')
    
    # Create a profile only if the application is using
    # EmoryLDAPUserProfile. If you want to use anything else, you'll need to
    # create your own post_save handler.
    auth_profile = getattr(settings, 'AUTH_PROFILE_MODULE', None)
    if created and auth_profile == 'emory.EmoryLDAPUserProfile':
        profile = EmoryLDAPUserProfile(user=instance)
        profile.save()
post_save.connect(create_profile, sender=User)
