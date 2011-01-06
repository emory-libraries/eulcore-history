# file fedora/models.py
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

import cStringIO
import hashlib
import logging

from rdflib import URIRef, Graph as RdfGraph

from lxml import etree
from lxml.builder import ElementMaker

from eulcore import xmlmap
from eulcore.fedora.rdfns import model as modelns
from eulcore.fedora.util import parse_xml_object, parse_rdf, RequestFailed, datetime_to_fedoratime
from eulcore.fedora.xml import ObjectDatastreams, ObjectProfile, DatastreamProfile, \
    NewPids, ObjectHistory, ObjectMethods, DsCompositeModel
from eulcore.xmlmap.dc import DublinCore

logger = logging.getLogger(__name__)

class DatastreamObject(object):
    """Object to ease accessing and updating a datastream belonging to a Fedora
    object.  Handles datastream content as well as datastream profile information.
    Content and datastream info are only pulled from Fedora when content and info
    fields are accessed.

    Intended to be used with :class:`DigitalObject` and intialized
    via :class:`Datastream`.  

    Initialization parameters:
        :param obj: the :class:`DigitalObject` that this datastream belongs to.
        :param id: datastream id
        :param label: default datastream label
        :param mimetype: default datastream mimetype
        :param versionable: default configuration for datastream versioning
        :param state: default configuration for datastream state
        :param format: default configuration for datastream format URI
        :param checksum: default configuration for datastream checksum
        :param format: default configuration for datastream checksum type 
    """
    default_mimetype = "application/octet-stream"
    def __init__(self, obj, id, label, mimetype=None, versionable=False,
            state='A', format=None, control_group='M', checksum=None, checksum_type="MD5"):
                        
        self.obj = obj
        self.id = id

        if mimetype is None:
            mimetype = self.default_mimetype

        self.defaults = {
            'label': label,
            'mimetype': mimetype,
            'versionable': versionable,
            'state' : state,
            'format': format,
            'control_group': control_group,
            'checksum': checksum,
            'checksumType': checksum_type,
        }
        self._info = None
        self._content = None
        # for unversioned datastreams, store a copy of data pulled from fedora in case undo save is required
        self._info_backup = None
        self._content_backup = None

        self.info_modified = False
        self.digest = None
        self.checksum_modified = False
        
        #Indicates whether the datastream exists in fedora.
	self.exists = False        
        #If this is an object with a real pid, then check if the datastream is actually there. If it does, exists should be true.
	if not self.obj._create:
            if self.obj.ds_list.has_key(id):
                self.exists = True
    
    @property
    def info(self):
        # pull datastream profile information from Fedora, but only when accessed
        if self._info is None:
            if not self.exists:
                self._info = self._bootstrap_info()
            else:
                self._info = self.obj.getDatastreamProfile(self.id)
        return self._info

    def _bootstrap_info(self):
        profile = DatastreamProfile()
        profile.state = self.defaults['state']
        profile.mimetype = self.defaults['mimetype']
        profile.control_group = self.defaults['control_group']
        profile.versionable = self.defaults['versionable']
        if self.defaults.get('label', None):
            profile.label = self.defaults['label']
        if self.defaults.get('format', None):
            profile.format = self.defaults['format']
        return profile

    def _get_content(self):
        # pull datastream content from Fedora, but only when accessed
        if self._content is None:
            if not self.exists:
                self._content = self._bootstrap_content()
            else:
                data, url = self.obj.api.getDatastreamDissemination(self.obj.pid, self.id)
                self._content = self._convert_content(data, url)
                # calculate and store a digest of the current datastream text content
                self.digest = self._content_digest()
        return self._content
    def _set_content(self, val):
        # if datastream is not versionable, grab contents before updating
        if not self.versionable:
            self._get_content()
        self._content = val
    content = property(_get_content, _set_content, None,
        "contents of the datastream; only pulled from Fedora when accessed, cached after first access")

    def _convert_content(self, data, url):
        # convert output of getDatastreamDissemination into the expected content type
        return data

    def _bootstrap_content(self):
        return None

    def _content_as_node(self):
        # used for serializing inline xml datastreams at ingest
        return None

    def _raw_content(self):
        # return datastream content in the appropriate format to be saved to Fedora
        # (normally, either a string or a file); used for serializing
        # managed datastreams for ingest and save and generating a hash
        # NOTE: if you override so this does not return a string, you may
        # also need to override _content_digest and/or isModified
        if self.content is None:
            return None
        if hasattr(self.content, 'serialize'):
            return str(self.content.serialize())
        else:
            return str(self.content)

    def isModified(self):
        """Check if either the datastream content or profile fields have changed
        and should be saved to Fedora.
        
        :rtype: boolean
        """
        return self.info_modified or self._content_digest() != self.digest

    def _content_digest(self):
        # generate a hash of the content so we can easily check if it has changed and should be saved
        return hashlib.sha1(self._raw_content()).hexdigest()

    ### access to datastream profile fields; tracks if changes are made for saving to Fedora

    def _get_label(self):
        return self.info.label
    def _set_label(self, val):
        self.info.label = val
        self.info_modified = True    
    label = property(_get_label, _set_label, None, "datastream label")
    
    def _get_mimetype(self):
        return self.info.mimetype
    def _set_mimetype(self, val):
        self.info.mimetype = val
        self.info_modified = True
    mimetype = property(_get_mimetype, _set_mimetype, None, "datastream mimetype")

    def _get_versionable(self):
        return self.info.versionable
    def _set_versionable(self, val):
        self.info.versionable = val
        self.info_modified = True
    versionable = property(_get_versionable, _set_versionable, None,
        "boolean; indicates if Fedora is configured to version the datastream")

    def _get_state(self):
        return self.info.state
    def _set_state(self, val):
        self.info.state = val
        self.info_modified = True
    state = property(_get_state, _set_state, None, "datastream state (Active/Inactive/Deleted)")

    def _get_format(self):
        return self.info.format
    def _set_format(self, val):
        self.info.format = val
        self.info_modified = True
    format = property(_get_format, _set_format, "datastream format URI")
    
    def _get_checksum(self):
        return self.info.checksum
    def _set_checksum(self, val):
        self.info.checksum = val
        self.info_modified = True
        self.checksum_modified = True
    checksum = property(_get_checksum, _set_checksum, "datastream checksum")
    
    def _get_checksumType(self):
        return self.info.checksum_type
    def _set_checksumType(self, val):
        self.info.checksum_type = val
        self.info_modified = True
    checksum_type = property(_get_checksumType, _set_checksumType, "datastream checksumType")

    # read-only info properties

    @property 
    def control_group(self):
        return self.info.control_group

    @property
    def created(self):
        return self.info.created

    @property
    def modified(self):
        return self.info.modified

    def save(self, logmessage=None):
        """Save datastream content and any changed datastream profile
        information to Fedora.

        :rtype: boolean for success
        """
        data = self._raw_content()

        modify_opts = {}
        if self.info_modified:
            if self.label:
                modify_opts['dsLabel'] = self.label
            if self.mimetype:
                modify_opts['mimeType'] = self.mimetype
            if self.versionable is not None:
                modify_opts['versionable'] = self.versionable
            if self.state:
                modify_opts['dsState'] = self.state
            if self.format:
                modify_opts['formatURI'] = self.format
            if self.checksum:
                if(self.checksum_modified):
                    modify_opts['checksum'] = self.checksum
            if self.checksum_type:
                modify_opts['checksumType'] = self.checksum_type
            # FIXME: should be able to handle checksums
        # NOTE: as of Fedora 3.2, updating content without specifying mimetype fails (Fedora bug?)
        if 'mimeType' not in modify_opts.keys():
            # if datastreamProfile has not been pulled from fedora, use configured default mimetype
            if self._info is not None:
                modify_opts['mimeType'] = self.mimetype
            else:
                modify_opts['mimeType'] = self.defaults['mimetype']

        if not self.versionable:
            self._backup()
        
        if(self.exists):    
            success, msg = self.obj.api.modifyDatastream(self.obj.pid, self.id, content=data,
                    logMessage=logmessage, **modify_opts)
        else:
            success, msg = self.obj.api.addDatastream(self.obj.pid, self.id, controlGroup='M', content=data, logMessage=logmessage, **modify_opts)
            #If added successfully, set the exists flag to true.
            if success:
                self.exists = True
 
        if success:
            # update modification indicators
            self.info_modified = False
            self.checksum_modified = False
            self.digest = self._content_digest()
            
        return success      # msg ?

    def _backup(self):
        info = self.obj.getDatastreamProfile(self.id)
        self._info_backup = { 'dsLabel': info.label,
                              'mimeType': info.mimetype,
                              'versionable': info.versionable,
                              'dsState': info.state,
                              'formatURI': info.format,
                              'checksumType': info.checksum_type,
                              'checksum': info.checksum }

        data, url = self.obj.api.getDatastreamDissemination(self.obj.pid, self.id)
        self._content_backup = data

    def undo_last_save(self, logMessage=None):
        """Undo the last change made to the datastream content and profile, effectively 
        reverting to the object state in Fedora as of the specified timestamp.

        For a versioned datastream, this will purge the most recent datastream.
        For an unversioned datastream, this will overwrite the last changes with
        a cached version of any content and/or info pulled from Fedora.
        """        
        # NOTE: currently not clearing any of the object caches and backups
        # of fedora content and datastream info, as it is unclear what (if anything)
        # should be cleared

        if self.versionable:
            # if this is a versioned datastream, get datastream history
            # and purge the most recent version 
            history = self.obj.api.getDatastreamHistory(self.obj.pid, self.id)
            last_save = history.datastreams[0].createDate   # fedora returns with most recent first
            success, timestamps = self.obj.api.purgeDatastream(self.obj.pid, self.id, datetime_to_fedoratime(last_save),
                                                logMessage=logMessage)
            return success
        else:
            # for an unversioned datastream, update with any content and info
            # backups that were pulled from Fedora before any modifications were made
            args = {}
            if self._content_backup is not None:
                args['content'] = self._content_backup
            if self._info_backup is not None:
                args.update(self._info_backup)
            success, msg = self.obj.api.modifyDatastream(self.obj.pid, self.id,
                            logMessage=logMessage, **args)
            return success                   

class Datastream(object):
    """Datastream descriptor to simplify configuration and access to datastreams
    that belong to a particular :class:`DigitalObject`.

    When accessed, will initialize a :class:`DatastreamObject` and cache it on
    the :class:`DigitalObject` that it belongs to.

    Example usage::

        class MyDigitalObject(DigitalObject):
            text = Datastream("TEXT", "Text content", defaults={'mimetype': 'text/plain'})

    All other configuration defaults are passed on to the :class:`DatastreamObject`.
    """

    _datastreamClass = DatastreamObject

    def __init__(self, id, label, defaults={}):
        self.id = id
        self.label = label 
        self.datastream_args = defaults
        
        #self.label = label
        #self.datastream_defaults = defaults

    def __get__(self, obj, objtype): 
        if obj is None:
            return self
        if obj.dscache.get(self.id, None) is None:
            obj.dscache[self.id] = self._datastreamClass(obj, self.id, self.label, **self.datastream_args)
        return obj.dscache[self.id]

    @property
    def default_mimetype(self):
        mimetype = self.datastream_args.get('mimetype', None)
        if mimetype:
            return mimetype
        ds_cls = self._datastreamClass
        return ds_cls.default_mimetype

    @property
    def default_format_uri(self):
        return self.datastream_args.get('format', None)

    # set and delete not implemented on datastream descriptor
    # - delete would only make sense for optional datastreams, not yet needed
    # - saving updated content to fedora handled by datastream object


class XmlDatastreamObject(DatastreamObject):
    """Extends :class:`DatastreamObject` in order to initialize datastream content
    as an instance of a specified :class:`~eulcore.xmlmap.XmlObject`.

    See :class:`DatastreamObject` for more details.  Has one additional parameter:

    :param objtype: xml object type to use for datastream content; if not specified,
        defaults to :class:`~eulcore.xmlmap.XmlObject`
    """
    
    default_mimetype = "text/xml"

    def __init__(self, obj, id, label, objtype=xmlmap.XmlObject, **kwargs):
        self.objtype = objtype
        super(XmlDatastreamObject, self).__init__(obj, id, label, **kwargs)

    # FIXME: override _set_content to handle setting full xml content?

    def _convert_content(self, data, url):
        return parse_xml_object(self.objtype, data, url)

    def _bootstrap_content(self):
        return self.objtype()

    def _content_as_node(self):
        return self.content.node


class XmlDatastream(Datastream):
    """XML-specific version of :class:`Datastream`.  Datastreams are initialized
    as instances of :class:`XmlDatastreamObject`.  An additional, optional
    parameter ``objtype`` is passed to the Datastream object to configure the
    type of :class:`eulcore.xmlmap.XmlObject` that should be used for datastream
    content.

    Example usage::

        from eulcore.xmlmap.dc import DublinCore
        
        class MyDigitalObject(DigitalObject):
            dc = XmlDatastream("DC", "Dublin Core", DublinCore)


    """
    _datastreamClass = XmlDatastreamObject
    
    def __init__(self, id, label, objtype=None, defaults={}):        
        super(XmlDatastream, self).__init__(id, label, defaults)
        self.datastream_args['objtype'] = objtype


class RdfDatastreamObject(DatastreamObject):
    """Extends :class:`DatastreamObject` in order to initialize datastream content
    as an RDF graph.
    """
    default_mimetype = "application/rdf+xml"
    # prefixes for namespaces expected to be used in RELS-EXT
    default_namespaces = {
        'fedora-model': 'info:fedora/fedora-system:def/model#',
        'fedora-rels-ext': 'info:fedora/fedora-system:def/relations-external#'
        }

    # FIXME: override _set_content to handle setting content?
    def _convert_content(self, data, url):
        return self._bind_prefixes(parse_rdf(data, url))

    def _bootstrap_content(self):
        return self._bind_prefixes(RdfGraph())

    def _bind_prefixes(self, graph):
        # bind any specified prefixes so that serialized xml will be human-readable
        for prefix, namespace in self.default_namespaces.iteritems():
            graph.bind(prefix, namespace)
        return graph

    def _content_as_node(self):
        graph = self.content
        data = graph.serialize()
        obj = xmlmap.load_xmlobject_from_string(data)
        return obj.node

    def replace_uri(self, src, dest):
        """Replace a uri reference everywhere it appears in the graph with
        another one. It could appear as the subject, predicate, or object of
        a statement, so for each position loop through each statement that
        uses the reference in that position, remove the old statement, and
        add the replacement. """

        # NB: The hypothetical statement <src> <src> <src> will be removed
        # and re-added several times. The subject block will remove it and
        # add <dest> <src> <src>. The predicate block will remove that and
        # add <dest> <dest> <src>. The object block will then remove that
        # and add <dest> <dest> <dest>.

        # NB2: The list() call here is necessary. .triples() is a generator:
        # It calculates its matches as it progressively iterates through the
        # graph. Actively changing the graph inside the for loop while the
        # generator is in the middle of examining it risks invalidating the
        # generator and could conceivably make it Just Break, depending on
        # the implementation of .triples(). Wrapping .triples() in a list()
        # forces it to exhaust the generator, running through the entire
        # graph to calculate the list of matches before continuing to the
        # for loop.

        subject_triples = list(self.content.triples((src, None, None)))
        for s, p, o in subject_triples:
            self.content.remove((src, p, o))
            self.content.add((dest, p, o))

        predicate_triples = list(self.content.triples((None, src, None)))
        for s, p, o in predicate_triples:
            self.content.remove((s, src, o))
            self.content.add((s, dest, o))

        object_triples = list(self.content.triples((None, None, src)))
        for s, p, o in object_triples:
            self.content.remove((s, p, src))
            self.content.add((s, p, dest))

    def _prepare_ingest(self):
        """If the RDF datastream refers to the object by the default dummy
        uriref then we need to replace that dummy reference with a real one
        before we ingest the object."""

        # see also commentary on DigitalObject.DUMMY_URIREF
        self.replace_uri(self.obj.DUMMY_URIREF, self.obj.uriref)


class RdfDatastream(Datastream):
    """RDF-specific version of :class:`Datastream`.  Datastreams are initialized
    as instances of :class:`RdfDatastreamObject`.

    Example usage::

        class MyDigitalObject(DigitalObject):
            rels_ext = RdfDatastream("RELS-EXT", "External Relations")
    """
    _datastreamClass = RdfDatastreamObject


class FileDatastreamObject(DatastreamObject):
    """Extends :class:`DatastreamObject` in order to allow setting and reading
    datastream content as a file. To update contents, set datastream content
    property to a new file object. For example::

        class ImageObject(DigitalObject):
            image = FileDatastream('IMAGE', 'image datastream', defaults={
                'mimetype': 'image/png'
            })
    
    Then, with an instance of ImageObject::

        obj.image.content = open('/path/to/my/file')
        obj.save()
    """

    _content_modified = False

    def _raw_content(self):  
        return self.content     # return the file itself (handled by upload/save API calls)

    def _convert_content(self, data, url):
        # for now, using stringio to return a file-like object
        # NOTE: will require changes (here and in APIs) to handle large files
        return cStringIO.StringIO(data)

    # redefine content property to override set_content to set a flag when modified
    def _get_content(self):
        super(FileDatastreamObject, self)._get_content()
        return self._content    
    def _set_content(self, val):
        super(FileDatastreamObject, self)._set_content(val)
        self._content_modified = True        
    content = property(_get_content, _set_content, None,
        "contents of the datastream; only pulled from Fedora when accessed, cached after first access")

    def _content_digest(self):
        # don't attempt to create a checksum of the file content
        pass
    
    def isModified(self):
        return self.info_modified or self._content_modified
    

class FileDatastream(Datastream):
    """File-based content version of :class:`Datastream`.  Datastreams are
    initialized as instances of :class:`FileDatastreamObject`.
    """
    _datastreamClass = FileDatastreamObject


class DigitalObjectType(type):
    """A metaclass for :class:`DigitalObject`.
    
    All this does for now is find Datastream objects from parent classes
    and those defined on the class itself and collect them into a
    _defined_datastreams dictionary on the class. Using this, clients (or,
    more likely, internal library code) can more easily introspect the
    datastreams defined in code for the object.
    """

    _registry = {}

    def __new__(cls, name, bases, defined_attrs):
        datastreams = {}
        local_datastreams = {}
        use_attrs = defined_attrs.copy()

        for base in bases:
            base_ds = getattr(base, '_defined_datastreams', None)
            if base_ds:
                datastreams.update(base_ds)

        for attr_name, attr_val in defined_attrs.items():
            if isinstance(attr_val, Datastream):
                local_datastreams[attr_name] = attr_val

        use_attrs['_local_datastreams'] = local_datastreams

        datastreams.update(local_datastreams)
        use_attrs['_defined_datastreams'] = datastreams

        super_new = super(DigitalObjectType, cls).__new__
        new_class = super_new(cls, name, bases, use_attrs)

        new_class_name = '%s.%s' % (new_class.__module__, new_class.__name__)
        DigitalObjectType._registry[new_class_name] = new_class

        return new_class

    @property
    def defined_types(self):
        return DigitalObjectType._registry.copy()


class DigitalObject(object):
    """
    A single digital object in a Fedora respository, with methods and properties
    to easy creating, accessing, and updating a Fedora object or any of its component
    parts.
    """

    __metaclass__ = DigitalObjectType

    dc = XmlDatastream("DC", "Dublin Core", DublinCore, defaults={
            'control_group': 'X',
            'format': 'http://www.openarchives.org/OAI/2.0/oai_dc/',
        })
    rels_ext = RdfDatastream("RELS-EXT", "External Relations", defaults={
            'control_group': 'X',
            'format': 'info:fedora/fedora-system:FedoraRELSExt-1.0',
        })

    def __init__(self, api, pid=None, create=False):
        self.api = api
        self.dscache = {}       # accessed by DatastreamDescriptor to store and cache datastreams

        # cache object profile, track if it is modified and needs to be saved
        self._info = None
        self.info_modified = False
        
        # datastream list from fedora
        self._ds_list = None
        
        # object history
        self._history = None
        self._methods = None

        # pid = None signals to create a new object, using a default pid
        # generation function.
        if pid is None:
            # self._getDefaultPid is probably the method defined elsewhere
            # in this class. Barring clever hanky-panky, it should be
            # reliably callable.
            pid = self._getDefaultPid

        # callable(pid) signals a function to call to obtain a pid if and
        # when one is needed
        if callable(pid):
            create = True

        self.pid = pid

        self._create = bool(create)

        if create:
            self._init_as_new_object()

    def _init_as_new_object(self):
        for cmodel in getattr(self, 'CONTENT_MODELS', ()):
            self.rels_ext.content.add((self.uriref, modelns.hasModel,
                                       URIRef(cmodel)))

    def __str__(self):
        if callable(self.pid):
            return '(generated pid; uningested)'
        elif self._create:
            return self.pid + ' (uningested)'
        else:
            return self.pid

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, str(self))

    def _getDefaultPid(self, namespace=None):
        # This function is used by __init__ as a default pid generator if
        # none is specified. If you get the urge to override it, make sure
        # it still works there.
        kwargs = {}
        if namespace is not None:
            kwargs['namespace'] = namespace
        data, url = self.api.getNextPID(**kwargs)
        nextpids = parse_xml_object(NewPids, data, url)
        return nextpids.pids[0]

    @property
    def pidspace(self):
        "Fedora pidspace of this object"
        if callable(self.pid):
            return None
        ps, pid = self.pid.split(':', 1)
        return ps

    # This dummy pid stuff is ugly. I'd rather not need it. Every now and
    # then, though, something needs a PID or URI for a brand-new object
    # (i.e., with a callable self.pid) before we've even had a chance to
    # generate one. In particular, if we want to add statements to an
    # object's RELS-EXT, then the the object URI needs to be the subject of
    # those statements. We can't just generate the PID early because we get
    # PIDs from ARKs, and those things stick around. Also, most objects get
    # RELS-EXT statements right as we create them anyway (see references to
    # CONTENT_MODELS in _init_as_new_object()), so calling self.pid as soon
    # as we need a uri would be essentially equivalent to "at object
    # creation," which negates the whole point of lazy callable pids.
    #
    # So anyway, this DUMMY_PID gives us something we can use as a pid for
    # new objects, with the understanding that we have to clean it up to use
    # the real pid in obj._prepare_ingest(), which is called after we've
    # committed to trying to ingest the object, and thus after self.pid has
    # been called and replaced with a real string pid. DatastreamObject
    # subclasses can do this in their own _prepare_ingest() methods.
    # RELS-EXT (and all other RDF datastreams for that matter) get that
    # implemented in RdfDatastreamObject above.
    DUMMY_PID = 'TEMP:DUMMY_PID'
    DUMMY_URIREF = URIRef('info:fedora/' + DUMMY_PID)

    @property
    def uri(self):
        "Fedora URI for this object (info:fedora/foo:### form of object pid) "
        use_pid = self.pid
        if callable(use_pid):
            use_pid = self.DUMMY_PID
        return 'info:fedora/' + use_pid

    @property
    def uriref(self):
        "Fedora URI for this object, as an rdflib URI object"
        return URIRef(self.uri)

    @property
    def info(self):
        # pull object profile information from Fedora, but only when accessed
        if self._info is None:
            self._info = self.getProfile()
        return self._info
    
    # object info properties

    def _get_label(self):
        return self.info.label
    def _set_label(self, val):
        self.info.label = val
        self.info_modified = True       # only if new val is different!
    label = property(_get_label, _set_label, None, "object label")

    def _get_owner(self):
        return self.info.owner
    def _set_owner(self, val):
        self.info.owner = val
        self.info_modified = True
    owner = property(_get_owner, _set_owner, None, "object owner")

    def _get_state(self):
        return self.info.state
    def _set_state(self, val):
        self.info.state = val
        self.info_modified = True
    state = property(_get_state, _set_state, None, "object state (Active/Inactive/Deleted)")

    # read-only info properties
    @property       
    def created(self):
        return self.info.created

    @property
    def modified(self):
        return self.info.modified

    @property
    def exists(self):
        """Does the object exist in Fedora?"""

        # If we made the object under the pretext that it doesn't exist in
        # fedora yet, then assume it doesn't exist in fedora yet.
        if self._create:
            return False

        # If we can get a valid object profile, regardless of its contents,
        # then this object exists. If not, then it doesn't. 
        try:
            self.getProfile()
            return True
        except RequestFailed:
            return False

    def getDatastreamProfile(self, dsid):
        """Get information about a particular datastream belonging to this object.

        :param dsid: datastream id
        :rtype: :class:`DatastreamProfile`
        """
        # NOTE: used by DatastreamObject
        if self._create:
            return None

        data, url = self.api.getDatastream(self.pid, dsid)
        return parse_xml_object(DatastreamProfile, data, url)

    @property
    def history(self):
        if self._history is None:
            self.getHistory()
        return self._history

    def getHistory(self):
        if self._create:
            return None
        else:
            data, url = self.api.getObjectHistory(self.pid)
            history = parse_xml_object(ObjectHistory, data, url)
        self._history = [c for c in history.changed]
        return history

    def getProfile(self):    
        """Get information about this object (label, owner, date created, etc.).

        :rtype: :class:`ObjectProfile`
        """
        if self._create:
            return ObjectProfile()
        else:
            data, url = self.api.getObjectProfile(self.pid)
            return parse_xml_object(ObjectProfile, data, url)

    def _saveProfile(self, logMessage=None):
        if self._create:
            raise Exception("can't save profile information for a new object before it's ingested.")

        saved = self.api.modifyObject(self.pid, self.label, self.owner, self.state, logMessage)
        if saved:
            # profile info is no longer different than what is in Fedora
            self.info_modified = False
        return saved
    
    def save(self, logMessage=None):
        """Save to Fedora any parts of this object that have been modified (object
        profile or any datastream content or info).  If a failure occurs at any
        point on saving any of the parts of the object, will back out any changes that
        have been made and raise a :class:`DigitalObjectSaveFailure` with information
        about where the failure occurred and whether or not it was recoverable.

        If the object is new, ingest it. If object profile information has
        been modified before saving, this data is used in the ingest.
        Datastreams are initialized to sensible defaults: XML objects are
        created using their default constructor, and RDF graphs start
        empty. If they're updated before saving then those updates are
        included in the initial version. Datastream profile information is
        initialized from defaults specified in the :class:`Datastream`
        declaration, though it too can be overridden prior to the initial
        save.
        """
        
        if self._create:
            self._prepare_ingest()
            self._ingest(logMessage)
        else:
            self._save_existing(logMessage)
        
        #No errors, then return true
        return True

    def _save_existing(self, logMessage):
        # save an object that has already been ingested into fedora

        # - list of datastreams that should be saved
        to_save = [ds for ds, dsobj in self.dscache.iteritems() if dsobj.isModified()]
        # - track successfully saved datastreams, in case roll-back is necessary
        saved = []        
        # save modified datastreams
        for ds in to_save:
            if self.dscache[ds].save(logMessage):
                    saved.append(ds)
            else:
                # save datastream failed - back out any changes that have been made
                cleaned = self._undo_save(saved, 
                                          "failed saving %s, rolling back changes" % ds)
                raise DigitalObjectSaveFailure(self.pid, ds, to_save, saved, cleaned)

        # NOTE: to_save list in exception will never include profile; should it?

        # FIXME: catch exceptions on save, treat same as failure to save (?)

        # save object profile (if needed) after all modified datastreams have been successfully saved
        if self.info_modified:
            if not self._saveProfile(logMessage):
                cleaned = self._undo_save(saved, "failed to save object profile, rolling back changes")
                raise DigitalObjectSaveFailure(self.pid, "object profile", to_save, saved, cleaned)
            

    def _undo_save(self, datastreams, logMessage=None):
        """Takes a list of datastreams and a datetime, run undo save on all of them,
        and returns a list of the datastreams where the undo succeeded.

        :param datastreams: list of datastream ids (should be in self.dscache)
        :param logMessage: optional log message
        """
        return [ds for ds in datastreams if self.dscache[ds].undo_last_save(logMessage)]

    def _prepare_ingest(self):
        # This should only ever be called on newly-created objects, and only
        # immediately before ingest. It's used to clean up any rough edges
        # left over from being hewn from raw bits (instead of loaded from
        # the repo, like most other DigitalObjects are). In particular, see
        # the comments by DigitalObject.DUMMY_PID.

        if callable(self.pid):
            self.pid = self.pid()

        for dsname, ds in self._defined_datastreams.items():
            dsobj = getattr(self, dsname)
            if hasattr(dsobj, '_prepare_ingest'):
                dsobj._prepare_ingest()


    def _ingest(self, logMessage):
        foxml = self._build_foxml_for_ingest()
        returned_pid = self.api.ingest(foxml, logMessage)

        if returned_pid != self.pid:
            msg = ('fedora returned unexpected pid "%s" when trying to ' + 
                   'ingest object with pid "%s"') % \
                  (returned_pid, self.pid)
            raise Exception(msg)

        # then clean up the local object so that self knows it's dealing
        # with an ingested object now
        self._create = False
        self._info = None
        self.info_modified = False
        self.dscache = {}

    def _build_foxml_for_ingest(self, pretty=False):
        doc = self._build_foxml_doc()

        print_opts = {'encoding' : 'UTF-8'}
        if pretty: # for easier debug
            print_opts['pretty_print'] = True
        
        return etree.tostring(doc, **print_opts)

    FOXML_NS = 'info:fedora/fedora-system:def/foxml#'

    def _build_foxml_doc(self):
        # make an lxml element builder - default namespace is foxml, display with foxml prefix
        E = ElementMaker(namespace=self.FOXML_NS, nsmap={'foxml' : self.FOXML_NS })
        doc = E('digitalObject')
        doc.set('VERSION', '1.1')
        doc.set('PID', self.pid)
        doc.append(self._build_foxml_properties(E))
        
        # collect datastream definitions for ingest.
        for dsname, ds in self._defined_datastreams.items():
            dsobj = getattr(self, dsname)
            dsnode = self._build_foxml_datastream(E, ds.id, dsobj)
            if dsnode is not None:
                doc.append(dsnode)
        
        return doc

    def _build_foxml_properties(self, E):
        props = E('objectProperties')
        state = E('property')
        state.set('NAME', 'info:fedora/fedora-system:def/model#state')
        state.set('VALUE', self.state or 'A')
        props.append(state)

        if self.label:
            label = E('property')
            label.set('NAME', 'info:fedora/fedora-system:def/model#label')
            label.set('VALUE', self.label)
            props.append(label)
        
        if self.owner:
            owner = E('property')
            owner.set('NAME', 'info:fedora/fedora-system:def/model#ownerId')
            owner.set('VALUE', self.owner)
            props.append(owner)

        return props

    def _build_foxml_datastream(self, E, dsid, dsobj):

        # if we can't construct a content node then bail before constructing
        # any other nodes
        content_node = None
        if dsobj.control_group == 'X':
            content_node = self._build_foxml_inline_content(E, dsobj)
        elif dsobj.control_group == 'M':
            content_node = self._build_foxml_managed_content(E, dsobj)
        if content_node is None:
            return

        ds_xml = E('datastream')
        ds_xml.set('ID', dsid)
        ds_xml.set('CONTROL_GROUP', dsobj.control_group)
        ds_xml.set('STATE', dsobj.state)
        ds_xml.set('VERSIONABLE', str(dsobj.versionable).lower())

        ver_xml = E('datastreamVersion')
        ver_xml.set('ID', dsid + '.0')
        ver_xml.set('MIMETYPE', dsobj.mimetype)
        if dsobj.format:
            ver_xml.set('FORMAT_URI', dsobj.format)
        if dsobj.label:
            ver_xml.set('LABEL', dsobj.label)
        #Set the checksum, if available.
        if dsobj.checksum:
            digest_xml = E('contentDigest')
            digest_xml.set('TYPE', "MD5")
            digest_xml.set('DIGEST', dsobj.checksum)
            ver_xml.append(digest_xml)
            
        ds_xml.append(ver_xml)

        ver_xml.append(content_node)
        return ds_xml

    def _build_foxml_inline_content(self, E, dsobj):
        orig_content_node = dsobj._content_as_node()
        if orig_content_node is None:
            return

        content_container_xml = E('xmlContent')
        content_container_xml.append(orig_content_node)
        return content_container_xml

    def _build_foxml_managed_content(self, E, dsobj):
        content_s = dsobj._raw_content()
        if content_s is None:
            return

        upload_id = self.api.upload(content_s)
        content_location = E('contentLocation')
        content_location.set('REF', upload_id)
        content_location.set('TYPE', 'INTERNAL_ID')
        return content_location

    def _get_datastreams(self):
        """
        Get all datastreams that belong to this object.

        Returns a dictionary; key is datastream id, value is an :class:`ObjectDatastream`
        for that datastream.

        :rtype: dictionary
        """
        if self._create:
            # FIXME: should we default to the datastreams defined in code?
            return {}
        else:
            # NOTE: can be accessed as a cached class property via ds_list
            data, url = self.api.listDatastreams(self.pid)
            dsobj = parse_xml_object(ObjectDatastreams, data, url)
            return dict([ (ds.dsid, ds) for ds in dsobj.datastreams ])

    @property
    def ds_list(self):      # NOTE: how to name to distinguish from locally configured datastream objects?
        """
        Dictionary of all datastreams that belong to this object in Fedora.
        Key is datastream id, value is an :class:`ObjectDatastream` for that
        datastream.

        Only retrieved when requested; cached after first retrieval.
        """
        # FIXME: how to make access to a versioned ds_list ?

        if self._ds_list is None:
            self._ds_list = self._get_datastreams()
        return self._ds_list

    @property
    def methods(self):
        if self._methods is None:
            self.get_methods()
        return self._methods

    def get_methods(self):
        if self._create:
            return {}

        data, url = self.api.listMethods(self.pid)
        methods = parse_xml_object(ObjectMethods, data, url)
        self._methods = dict((sdef.pid, sdef.methods)
                             for sdef in methods.service_definitions)
        return self._methods

    def getDissemination(self, service_pid, method, params={}):
        return self.api.getDissemination(self.pid, service_pid, method, method_params=params)

    def getDatastreamObject(self, dsid):
        "Get any datastream on this object as a :class:`DatastreamObject`"
        if dsid in self.ds_list:
            ds_info = self.ds_list[dsid]
            # FIXME: can we take advantage of Datastream descriptor? or at least use dscashe ?            
            return DatastreamObject(self, dsid, label=ds_info.label, mimetype=ds_info.mimeType)
        # exception if not ?

    def add_relationship(self, rel_uri, object):
        """
        Add a new relationship to the RELS-EXT for this object.
        Calls :meth:`API_M.addRelationship`.

        Example usage::

            isMemberOfCollection = "info:fedora/fedora-system:def/relations-external#isMemberOfCollection"
            collection_uri = "info:fedora/foo:456"
            object.add_relationship(isMemberOfCollection, collection_uri)

        :param rel_uri: URI for the new relationship
        :param object: related object; can be :class:`DigitalObject` or string; if
                        string begins with info:fedora/ it will be treated as
                        a resource, otherwise it will be treated as a literal
        :rtype: boolean
        """  
        if isinstance(rel_uri, URIRef):
            rel_uri = unicode(rel_uri)

        obj_is_literal = True
        if isinstance(object, DigitalObject):
            object = object.uri
            obj_is_literal = False
        elif isinstance(object, str) and object.startswith('info:fedora/'):
            obj_is_literal = False

        # this call will change RELS-EXT, possibly creating it if it's
        # missing. remove any cached info we have for that datastream.
        if 'RELS-EXT' in self.dscache:
            del self.dscache['RELS-EXT']
        self._ds_list = None

        return self.api.addRelationship(self.pid, rel_uri, object, obj_is_literal)

    def has_model(self, model):
        """
        Check if this object subscribes to the specified content model.

        :param model: URI for the content model, as a string
                    (currently only accepted in info:fedora/foo:### format)
        :rtype: boolean
        """
        # TODO:
        # - accept DigitalObject for model?
        # - convert model pid to info:fedora/ form if not passed in that way?
        try:
            rels = self.rels_ext.content
        except RequestFailed, e:
            # if rels-ext can't be retrieved, confirm this object does not have a RELS-EXT
            # (in which case, it does not subscribe to the specified content model)            
            if "RELS-EXT" not in self.ds_list.keys():
                return False
            else:
                raise Exception(e)            
            
        st = (self.uriref, modelns.hasModel, URIRef(model))
        return st in rels


class ContentModel(DigitalObject):
    """Fedora CModel object"""

    CONTENT_MODELS = ['info:fedora/fedora-system:ContentModel-3.0']
    ds_composite_model = XmlDatastream('DS-COMPOSITE-MODEL',
            'Datastream Composite Model', DsCompositeModel, defaults={
                'format': 'info:fedora/fedora-system:FedoraDSCompositeModel-1.0',
                'control_group': 'X',
                'versionable': True,
            })

    @staticmethod
    def for_class(cls, repo):
        full_name = '%s.%s' % (cls.__module__, cls.__name__)
        cmodels = getattr(cls, 'CONTENT_MODELS', None)
        if not cmodels:
            logger.debug('%s has no content models' % (full_name,))
            return None
        if len(cmodels) > 1:
            logger.debug('%s has %d content models' % (full_name, len(cmodels)))
            raise ValueError(('Cannot construct ContentModel object for ' +
                              '%s, which has %d CONTENT_MODELS (only 1 is ' +
                              'supported)') %
                             (full_name, len(cmodels)))

        cmodel_uri = cmodels[0]
        logger.debug('cmodel for %s is %s' % (full_name, cmodel_uri))
        cmodel_obj = repo.get_object(cmodel_uri, type=ContentModel,
                                     create=False)
        if cmodel_obj.exists:
            logger.debug('%s already exists' % (cmodel_uri,))
            return cmodel_obj

        # otherwise the cmodel doesn't exist. let's create it.
        logger.debug('creating %s from %s' % (cmodel_uri, full_name))
        cmodel_obj = repo.get_object(cmodel_uri, type=ContentModel,
                                     create=True)
        # XXX: should this use _defined_datastreams instead?
        for ds in cls._local_datastreams.values():
            ds_composite_model = cmodel_obj.ds_composite_model.content
            type_model = ds_composite_model.get_type_model(ds.id, create=True)
            type_model.mimetype = ds.default_mimetype
            if ds.default_format_uri:
                type_model.format_uri = ds.default_format_uri
        cmodel_obj.save()
        return cmodel_obj


class DigitalObjectSaveFailure(StandardError):
    """Custom exception class for when a save error occurs part-way through saving 
    an instance of :class:`DigitalObject`.  This exception should contain enough
    information to determine where the save failed, and whether or not any changes
    saved before the failure were successfully rolled back.

    These properties are available:
     * obj_pid - pid of the :class:`DigitalObject` instance that failed to save
     * failure - string indicating where the failure occurred (either a datastream ID or 'object profile')
     * to_be_saved - list of datastreams that were modified and should have been saved
     * saved - list of datastreams that were successfully saved before failure occurred
     * cleaned - list of saved datastreams that were successfully rolled back
     * not_cleaned - saved datastreams that were not rolled back
     * recovered - boolean, True indicates all saved datastreams were rolled back
    
    """
    def __init__(self, pid, failure, to_be_saved, saved, cleaned):
        self.obj_pid = pid
        self.failure = failure
        self.to_be_saved = to_be_saved
        self.saved = saved
        self.cleaned = cleaned
        # check for anything was saved before failure occurred that was *not* cleaned up
        self.not_cleaned = [item for item in self.saved if not item in self.cleaned]
        self.recovered = (len(self.not_cleaned) == 0)

    def __str__(self):
        return "Error saving %s - failed to save %s; saved %s; successfully backed out %s" \
                % (self.obj_pid, self.failure, ', '.join(self.saved), ', '.join(self.cleaned))
        
