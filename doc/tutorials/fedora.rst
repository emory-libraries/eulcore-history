Creating a simple Django app for Fedora Commons repository content
==================================================================

This is a tutorial to walk you through using EULcore with Django to build
a simple interface to the Fedora-Commons repository for uploading files,
viewing uploaded files in the repository, editing Dublin Core metadata,
and searching content in the repository.

This tutorial assumes that you have `Django`_ installed and an
installation of the `Fedora Commons repository`_ available to interact
with.  You should have some familiarity with Python and Django (at the
very least, you should have worked through the `Django
Tutorial`_). You should also have some familiarity with the Fedora
Commons Repository and a basic understanding of objects and content
models in Fedora.

.. _Django: http://www.djangoproject.com/
.. _Django Tutorial: http://docs.djangoproject.com/en/1.2/intro/tutorial01/
.. _Fedora Commons repository: http://www.fedora-commons.org/

We will use ``pip`` to install EULcore and its dependencies; on some
platforms (most notably, in Windows), you may need to install some of
the python dependencies manually; see :ref:`Dependencies` for more details.


Create a new Django project and setup :mod:`eulcore.django.fedora`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use ``pip`` to install the eulcore library and its dependencies.  For this tutorial,
we'll use the latest tagged release of EULcore, 0.11 ::

    pip install svn+https://svn.library.emory.edu/svn/python-eulcore/tags/release-0.11.0

This command should install EULcore and its Python dependencies; if
you have difficulty, see :ref:`Dependencies`.

Now, let's go ahead and create a new Django project.  We'll call it *simplerepo*::

    django-admin.py startproject simplerepo

Go ahead and do some minimal configuration in your django settings.  For simplicity,
you can use a sqlite database for this tutorial (in fact, we won't make much use of
this database).

In addition to the standard Django settings, add :mod:`eulcore.django.fedora`
to your ``INSTALLED_APPS`` and add Fedora connection configurations to your
``settings.py`` so that the :mod:`eulcore.fedora`
:class:`~eulcore.django.fedora.server.Repository` object can automatically
connect to your configured Fedora repository::

    # Fedora Repository settings
    FEDORA_ROOT = 'https://localhost:8543/fedora/'
    FEDORA_USER = 'fedoraAdmin'
    FEDORA_PASS = 'fedoraAdmin'
    FEDORA_PIDSPACE = 'simplerepo'

Since we're planning to upload content into Fedora, make sure you are using a fedora user account that has permission
to upload, ingest, and modify content.

Create a model for your Fedora object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before we can upload any content, we need to create an object to represent how we want to store that data in Fedora.
Let's create a new Django app where we will create this model and associated views::

    python manage.py startapp repo

In ``repo/models.py``, create a class that extends :class:`~eulcore.fedora.models.DigitalObject`::

    from eulcore.fedora.models import DigitalObject, FileDatastream

    class FileObject(DigitalObject):
        FILE_CONTENT_MODEL = 'info:fedora/eulctl:File-1.0'
        CONTENT_MODELS = [ FILE_CONTENT_MODEL ]
        file = FileDatastream("FILE", "Binary datastream", defaults={
                'versionable': True,
        })

What we're doing here extending the default :class:`~eulcore.fedora.models.DigitalObject`, which gives us Dublin Core
and RELS-EXT datastream mappings for free, since those are part of every Fedora object.  In addition, we're defining
a custom datastream that we will use to store the binary files that we're going to upload for ingest into Fedora.  This
configures a versionable :class:`~eulcore.fedora.models.FileDatastream` with a datastream id of ``FILE`` and a default
datastream label of ``Binary Datastream``.  We could also set a default mimetype here, if we wanted.

Let's inspect our new model object in the Django console for a moment::

    python manage.py shell

The easiest way to initialize a new object is to use the Repository object ``get_object`` method, which can also be used
to access existing Fedora objects.  Using the Repository object allows us to seamlessly pass along the Fedora
connection configuration that the Repository object picks up from your django ``settings.py``::

    >>> from eulcore.django.fedora import Repository
    >>> from simplerepo.repo.models import FileObject

    # initialize a connection to the configured Fedora repository instance
    >>> repo = Repository()

    # create a new FileObject instance
    >>> obj = repo.get_object(type=FileObject)
    # this is an uningested object; it will get the default type of generated pid when we save it
    >>> obj
    <FileObject (generated pid; uningested)>

    # every DigitalObject has Dublin Core
    >>> obj.dc
    <eulcore.fedora.models.XmlDatastreamObject object at 0xa56f4ec>
    # dc.content is where you access and update the actual content of the datastream
    >>> obj.dc.content
    <eulcore.xmlmap.dc.DublinCore object at 0xa5681ec>
    # print out the content of the DC datastream - nothing there (yet)
    >>> print obj.dc.content.serialize(pretty=True)
    <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:dc="http://purl.org/dc/elements/1.1/"/>

    # every DigitalObject also gets rels_ext for free
    >>> obj.rels_ext
    <eulcore.fedora.models.RdfDatastreamObject object at 0xa56866c>
    # this is an RDF datastream, so the content uses rdflib instead of :mod:`eulcore.xmlmap`
    >>> obj.rels_ext.content
    <Graph identifier=omYiNhtw0 (<class 'rdflib.graph.Graph'>)>
    # print out the content of the rels_ext datastream
    # notice that it has a content-model relation defined based on our class definition
    >>> print obj.rels_ext.content.serialize(pretty=True)
    <?xml version="1.0" encoding="UTF-8"?>
    <rdf:RDF
       xmlns:fedora-model="info:fedora/fedora-system:def/model#"
       xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    >
      <rdf:Description rdf:about="info:fedora/TEMP:DUMMY_PID">
        <fedora-model:hasModel rdf:resource="info:fedora/eulctl:File-1.0"/>
      </rdf:Description>
    </rdf:RDF>

    # our FileObject also has a custom file datastream, but there's no content yet
    >>> obj.file
    <eulcore.fedora.models.FileDatastreamObject object at 0xa56ffac>

    # save the object to Fedora
    >>> obj.save()

    # our object now has a pid that was automatically generated by Fedora
    >>> obj.pid
    'simplerepo:1'
    # the object also has information about when it was created, modified, etc
    >>> obj.created
    datetime.datetime(2011, 3, 16, 19, 22, 46, 317000, tzinfo=tzutc())
    >>> print obj.created
    2011-03-16 19:22:46.317000+00:00
    # datastreams have this kind of information as well
    >>> print obj.dc.mimetype
    text/xml
    >>> print obj.dc.created
    2011-03-16 19:22:46.384000+00:00

    # we can modify the content and save the changes
    >>> obj.dc.content.title = 'My SimpleRepo test object'
    >>> obj.save()

We've defined a FileObject with a custom content model, but we haven't created the content model object in Fedora yet.
For simple content models, we can do this with a custom django manage.py command.  Run it in verbose mode so you can
more details about what it is doing::

    python manage.py syncrepo -v 2


You should see some output indicating that content models were generated for the class you just defined.

This command was is analogous to the Django ``syncdb`` command.  It looks through your models for classes that extend
DigitalObject, and when it finds content models defined that it can generate, which don't already exist in the
configured repository, it will generate them and ingest them into Fedora.  It can also be used to load initial objects
by way of simple XML filters.


Create a view to upload content
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

So, we have a Fedora DigitalObject defined.  Let's do something with it now.

Display an upload form
----------------------

We haven't defined any url patterns yet, so let's create a ``urls.py`` for our repo app and hook that into the main
project urls.  Create ``repo/urls.py`` with this content::

    from django.conf.urls.defaults import *

    urlpatterns = patterns('simplerepo.repo.views',
        url(r'^upload/$', 'upload', name='upload'),
    )

Then include that in your project ``urls.py``::

    (r'^', include('eulrepo.repo.urls')),

Now, let's define a simple upload form and a view method to correspond to that url.  First, for the form,
create a file named ``repo/forms.py`` and add the following::

    from django import forms

    class UploadForm(forms.Form):
        label = forms.CharField(max_length=255, # fedora label maxes out at 255 characters
                    help_text='Preliminary title for the new object. 255 characters max.')
        file = forms.FileField()

The minimum we need to create a new FileObject in Fedora is a file to ingest and a label for the object in Fedora.
We're could actually make the label optional here, because we could use the file name as a preliminary label, but for
simplicity let's require it.

Now, define an upload view to use this form.  For now, we're just going to display the form on GET; we'll add the
form processing in a moment.  Edit ``repo/views.py`` and add::

    from django.shortcuts import render_to_response
    from django.template import RequestContext
    from simplerepo.repo.forms import UploadForm

    def upload(request):
        if request.method == 'GET':
               form = UploadForm()

        return render_to_response('repo/upload.html', {'form': form}, context_instance=RequestContext(request))

But we still need a template to display our form.  Create a template directory and add it to your ``TEMPLATE_DIRS``
configuration in ``settings.py``.  Create a ``repo`` directory inside your template directory, and then create
``upload.html`` inside that directory and give it this content::

    <form method="post" enctype="multipart/form-data">{% csrf_token %}
        {{ form.as_p }}
        <input type="submit" value="Submit"/>
    </form>

Let's start the django server and make sure everything is working so far.  Start the server::

    $ python manage.py runserver

Then load `http://localhost:8000/upload/ <http://localhost:8000/upload/>`_ in your Web browser.  You should see a simple
upload form with the two fields defined.

Process the upload
------------------

Ok, but our view doesn't do anything yet when you submit the web form.  Let's add some logic to process the form.  We
need to import the Repository and FileObject classes and use the posted form data to initialize and save a new object,
rather like what we did earlier when we were investigating FileObject in the console.   Modify your ``repo/views.py``
so it looks like this::

    from django.shortcuts import render_to_response
    from django.template import RequestContext
    
    from eulcore.django.fedora.server import Repository

    from simplerepo.repo.forms import UploadForm
    from simplerepo.repo.models import FileObject

    def upload(request):
        obj = None
        if request.method == 'POST':
            form = UploadForm(request.POST, request.FILES)
            if form.is_valid():
                # initialize a connection to the repository and create a new FileObject
                repo = Repository()
                obj = repo.get_object(type=FileObject)
                # set the file datastream content to use the django UploadedFile object
                obj.file.content = request.FILES['file']
                # use the browser-supplied mimetype for now, even though we know this is unreliable
                obj.file.mimetype = request.FILES['file'].content_type
                # let's store the original file name as the datastream label
                obj.file.label = request.FILES['file'].name
                # set the initial object label from the form as the object label and the dc:title
                obj.label = form.cleaned_data['label']
                obj.dc.content.title = form.cleaned_data['label']
                obj.save()

                # re-init an empty upload form for additional uploads
                form = UploadForm()

        elif request.method == 'GET':
               form = UploadForm()

        return render_to_response('repo/upload.html', {'form': form, 'obj': obj},
            context_instance=RequestContext(request))

When content is posted to this view, we're binding our form to the request data and, when the form is valid,
creating a new FileObject and initializing it with the label and file that were posted, and saving it.  The view is
now passing that object to the template, so if it is defined that should mean we've successfully ingested content into
Fedora.  Let's update our template to show something if that is defined.  Add this to ``repo/upload.html`` before the
form is displayed::

    {% if obj %}
        <p>Successfully ingested {{ obj.label }} as {{ obj.pid }}.</p>
        <hr/>
        {# re-display the form to allow additional uploads #}
        <p>Upload another file?</p>
    {% endif %}

Go back to the upload page in your web browser.  Go ahead and enter a
label, select a file, and submit the form.  If all goes well, you should see a the message we added to the template for
successful ingest, along with the pid of the object you just created.

.. TODO: error handling (e.g., permission denied on ingest)



