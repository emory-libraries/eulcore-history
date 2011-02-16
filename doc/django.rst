:mod:`eulcore.django` -- Extensions and additions to django
======================================================================

.. automodule:: eulcore.django


:mod:`~eulcore.django.auth` - Customized permission decorators
--------------------------------------------------------------

.. automodule:: eulcore.django.auth

.. automethod:: eulcore.django.auth.user_passes_test_with_403

.. automethod:: eulcore.django.auth.permission_required_with_403



:mod:`~eulcore.django.emory_ldap` - Emory-specific LDAP support
---------------------------------------------------------------

.. module:: eulcore.django.emory_ldap

This module contains LDAP support specific to Emory University. Emory
developers who want more than the simple LDAP support as described in
:mod:`eulcore.django.ldap.backends` may want to use the more complete
support offered by this module in place of that one.

Applications that want to use full Emory LDAP support should:

   * Include :mod:`eulcore.django.emory_ldap` in ``INSTALLED_APPS``. This
     will create a new user profile model
     :class:`~eulcore.django.emory_ldap.models.EmoryLDAPUserProfile` and
     ensure that each new user created also gets one. It also enables the
     :program:`inituser` command in ``manage.py``.
   * Set the ``AUTH_PROFILE_MODULE`` setting to
     ``emory_ldap.EmoryLDAPUserProfile``, which makes the new
     :class:`EmoryLDAPUserProfile` data available through the user’s
     `get_profile() <http://docs.djangoproject.com/en/dev/topics/auth/#django.contrib.auth.models.User.get_profile>`_
     method.
   * Configure the LDAP authentication system as described for
     :mod:`eulcore.django.ldap.backends`::

        AUTH_LDAP_SERVER = 'ldaps://ldap.example.com'
        AUTH_LDAP_BASE_USER = 'cn=example,o=example.com'
        AUTH_LDAP_BASE_PASS = 's00p3rs33kr!t'
        AUTH_LDAP_SEARCH_SUFFIX = 'o=emory.edu'
        AUTH_LDAP_SEARCH_FILTER = '(uid=%s)'
        AUTH_LDAP_CHECK_SERVER_CERT = True
        AUTH_LDAP_CA_CERT_PATH = '/path/to/trusted/certs.pem'

   * Include :class:`eulcore.django.emory_ldap.backends.EmoryLDAPBackend` in
     the ``AUTHENTICATION_BACKENDS`` setting. This backend automatically
     collects Emory LDAP attributes and includes them in the user’s
     :class:`~eulcore.django.emory_ldap.models.EmoryLDAPUserProfile`.
   * Consider using `south <http://south.aeracode.org/>`_ migrations, which
     are maintained in the distribution of this module, though they are not
     required.


:mod:`~eulcore.django.existdb` -- Django tie-ins for :mod:`eulcore.existdb`
---------------------------------------------------------------------------

.. include:: ../src/eulcore/django/existdb/README

.. automodule:: eulcore.django.existdb

.. automodule:: eulcore.django.existdb.db

   .. autoclass:: ExistDB

   .. autoclass:: ResultPaginator

.. automodule:: eulcore.django.existdb.manager
   :members:

.. automodule:: eulcore.django.existdb.models

   .. autoclass:: XmlModel

      Two use cases are particularly common. First, a developer may wish to
      use an ``XmlModel`` just like an :class:`~eulcore.xmlmap.XmlObject`,
      but with the added semantics of being eXist-backed::
      
        class StoredWidget(XmlModel):
            name = StringField("name")
            quantity = IntegerField("quantity")
            top_customers = StringListField("(order[@status='active']/customer)[position()<5]/name")
            objects = Manager("//widget")

      Second, if an :class:`~eulcore.xml.XmlObject` is defined elsewhere, an
      application developer might simply expose
      :class:`~eulcore.django.existdb.db.ExistDB` backed objects::

        class StoredThingie(XmlModel, Thingie):
            objects = Manager("/thingie")

      Of course, some applications ask for mixing these two cases, extending
      an existing :class:`~eulcore.xml.XmlObject` while adding
      application-specific fields::

        class CustomThingie(XmlModel, Thingie):
            best_foobar = StringField("qux/fnord[@application='myapp']/name")
            custom_detail = IntegerField("detail/@level")
            objects = Manager("/thingie")

      In addition to the fields inherited from
      :class:`~eulcore.xmlmap.XmlObject`, ``XmlModel`` objects have one
      extra field:

      .. attribute:: _managers

         A dictionary mapping manager names to
         :class:`~eulcore.django.existdb.manager.Manager` objects. This
         dictionary includes all of the managers defined on the model
         itself, though it does not currently include managers inherited
         from the model's parents.

Custom Template Tags
^^^^^^^^^^^^^^^^^^^^

.. automodule:: eulcore.django.existdb.templatetags.existdb
    :members:

:mod:`~eulcore.django.existdb` Management commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following management commands will be available when you include 
:mod:`eulcore.django.existdb` in your django ``INSTALLED_APPS`` and rely on
the existdb settings described above.

For more details on these commands, use ``manage.py <command> help``

 * **existdb_index** - update, remove, and show information about the index configuration
   for a collection index
 * **existdb_reindex** - reindex a collection index in exist


:mod:`~eulcore.django.fedora` -- Django tie-ins for :mod:`eulcore.fedora`
-------------------------------------------------------------------------

.. include:: ../src/eulcore/django/fedora/README

.. automodule:: eulcore.django.fedora

.. automodule:: eulcore.django.fedora.server

   .. autoclass:: Repository

:mod:`~eulcore.django.fedora.views` Fedora views
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: eulcore.django.fedora.views

   .. automethod:: eulcore.django.fedora.views.raw_datastream

:mod:`~eulcore.django.fedora` Management commands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following management commands will be available when you include
:mod:`eulcore.django.fedora` in your django ``INSTALLED_APPS`` and rely on
the existdb settings described above.

For more details on these commands, use ``manage.py <command> help``

 * **syncrepo** - load content models and fixture object to the configured
   fedora repository

:mod:`~eulcore.django.fedora` Template tags
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:mod:`eulcore.django.fedora` adds custom `template tags
<http://docs.djangoproject.com/en/1.2/topics/templates/#custom-tag-and-filter-libraries>`_
for use in templates.

fedora_access
~~~~~~~~~~~~~

Catch fedora failures and permission errors encountered during template
rendering::

   {% load fedora %}

   {% fedora_access %}
      <p>Try to access data on fedora objects which could be
        <span class='{{ obj.inaccessible_ds.content.field }}'>inaccessible</span>
        or when fedora is
        <span class='{{ obj.regular_ds.content.other_field }}'>down</span>.</p>
   {% permission_denied %}
      <p>Fall back to this content if the main body results in a permission
        error while trying to access fedora data.</p>
   {% fedora_failed %}
      <p>Fall back to this content if the main body runs into another error
        while trying to access fedora data.</p>
   {% end_fedora_access %}

The ``permission_denied`` and ``fedora_failed`` sections are optional. If
only ``permission_denied`` is present then non-permission errors will result
in the entire block rendering empty. If only ``fedora_failed`` is present
then that section will be used for all errors whether permission-related or
not. If neither is present then all errors will result in the entire block
rendering empty.

Note that when Django's ``TEMPLATE_DEBUG`` setting is on, it precludes all
error handling and displays the Django exception screen for all errors,
including fedora errors, even if you use this template tag. To disable this
Django internal functionality and see the effects of the ``fedora_access``
tag, add the following to your Django settings::

   TEMPLATE_DEBUG = False


:mod:`~eulcore.django.forms` - Django Form extensions, custom fields
--------------------------------------------------------------------

.. automodule:: eulcore.django.forms

.. autoclass:: eulcore.django.forms.XmlObjectForm
    :members:

.. automethod:: eulcore.django.forms.xmlobjectform_factory

.. autoclass:: eulcore.django.forms.SubformField
    :members:

Custom fields & widgets
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: eulcore.django.forms.fields.W3CDateField
    :members:
.. autoclass:: eulcore.django.forms.fields.W3CDateWidget
    :members:

.. autoclass:: eulcore.django.forms.fields.DynamicChoiceField
    :members:
.. autoclass:: eulcore.django.forms.fields.DynamicSelect
    :members:


reCAPTCHA  for django forms
~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: eulcore.django.forms.captchafield

.. autoclass:: eulcore.django.forms.captchafield.ReCaptchaWidget
    :members:

.. autoclass:: eulcore.django.forms.captchafield.ReCaptchaField
    :members:


:mod:`~eulcore.django.http` - Content Negotiation for Django views
------------------------------------------------------------------

.. automodule:: eulcore.django.http

.. automethod:: eulcore.django.http.content_negotiation


:mod:`~eulcore.django.ldap.backends` - Django LDAP authentication
-----------------------------------------------------------------

.. automodule:: eulcore.django.ldap.backends

.. autoclass:: LDAPBackend
      :members:
      

:mod:`~eulcore.django.log`
---------------------------

.. automodule:: eulcore.django.log
    :members:


:mod:`~eulcore.django.test` - Django test extensions
----------------------------------------------------

.. automodule:: eulcore.django.test

.. autoclass:: TestCase
        :members:

        Example use of exist fixtures.  This will load the index configuration file,
        and then load all .xml files in the specified directory to the configured
        exist test collection.
        
        .. code-block:: python
        
          class MyExistViewsTest(eulcore.django.test.TestCase):
               exist_fixtures = { 'index' : exist_index_path,
                                  'directory' : exist_fixture_path }

        Note that testing with eXist full-text indexing is significantly slower
        than without, since every time eXist loads new documents (which happens
        every setUp), they must be reindexd.

:mod:`~eulcore.django.taskresult`
---------------------------------

.. automodule:: eulcore.django.taskresult
    :members:
