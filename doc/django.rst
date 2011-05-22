:mod:`eullocal.django` -- Extensions and additions to django
============================================================

.. automodule:: eullocal.django


:mod:`~eullocal.django.emory_ldap` - Emory-specific LDAP support
----------------------------------------------------------------

.. module:: eullocal.django.emory_ldap

This module contains LDAP support specific to Emory University. Emory
developers who want more than the simple LDAP support as described in
:mod:`eullocal.django.ldap.backends` may want to use the more complete
support offered by this module in place of that one.

Applications that want to use full Emory LDAP support should:

   * Include :mod:`eullocal.django.emory_ldap` in ``INSTALLED_APPS``. This
     will create a new user profile model
     :class:`~eullocal.django.emory_ldap.models.EmoryLDAPUserProfile` and
     ensure that each new user created also gets one. It also enables the
     :program:`inituser` command in ``manage.py``.
   * Set the ``AUTH_PROFILE_MODULE`` setting to
     ``emory_ldap.EmoryLDAPUserProfile``, which makes the new
     :class:`EmoryLDAPUserProfile` data available through the user’s
     `get_profile() <http://docs.djangoproject.com/en/dev/topics/auth/#django.contrib.auth.models.User.get_profile>`_
     method.
   * Configure the LDAP authentication system as described for
     :mod:`eullocal.django.ldap.backends`::

        AUTH_LDAP_SERVER = 'ldaps://ldap.example.com'
        AUTH_LDAP_BASE_USER = 'cn=example,o=example.com'
        AUTH_LDAP_BASE_PASS = 's00p3rs33kr!t'
        AUTH_LDAP_SEARCH_SUFFIX = 'o=emory.edu'
        AUTH_LDAP_SEARCH_FILTER = '(uid=%s)'
        AUTH_LDAP_CHECK_SERVER_CERT = True
        AUTH_LDAP_CA_CERT_PATH = '/path/to/trusted/certs.pem'

   * Include :class:`eullocal.django.emory_ldap.backends.EmoryLDAPBackend` in
     the ``AUTHENTICATION_BACKENDS`` setting. This backend automatically
     collects Emory LDAP attributes and includes them in the user’s
     :class:`~eullocal.django.emory_ldap.models.EmoryLDAPUserProfile`.
   * Consider using `south <http://south.aeracode.org/>`_ migrations, which
     are maintained in the distribution of this module, though they are not
     required.


:mod:`~eullocal.django.forms.captchafield` - reCAPTCHA  for django forms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. automodule:: eullocal.django.forms.captchafield

.. autoclass:: eullocal.django.forms.captchafield.ReCaptchaWidget
    :members:

.. autoclass:: eullocal.django.forms.captchafield.ReCaptchaField
    :members:


:mod:`~eullocal.django.ldap.backends` - Django LDAP authentication
------------------------------------------------------------------

.. automodule:: eullocal.django.ldap.backends

.. autoclass:: LDAPBackend
      :members:
      

:mod:`~eullocal.django.log`
---------------------------

.. automodule:: eullocal.django.log
    :members:


:mod:`~eullocal.django.taskresult`
----------------------------------

.. automodule:: eullocal.django.taskresult
    :members:
