import cStringIO
import hashlib
from rdflib import URIRef
from rdflib.Graph import Graph as RdfGraph

from lxml import etree
from lxml.builder import ElementMaker

from eulcore import xmlmap
from eulcore.fedora.util import parse_xml_object, parse_rdf, RequestFailed, datetime_to_fedoratime
from eulcore.fedora.xml import ObjectDatastreams, ObjectProfile, DatastreamProfile, \
    NewPids, ObjectHistory, ObjectMethods, DsCompositeModel
from eulcore.xmlmap.dc import DublinCore


# FIXME: needed by both server and models, where to put?
URI_HAS_MODEL = 'info:fedora/fedora-system:def/model#hasModel'

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
    """
    default_mimetype = "application/octet-stream"
    def __init__(self, obj, id, label, mimetype=None, versionable=False,
            state='A', format=None, control_group='M'):
                        
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
        }
        self._info = None
        self._content = None
        # for unversioned datastreams, store a copy of data pulled from fedora in case undo save is required
        self._info_backup = None
        self._content_backup = None

        self.info_modified = False
        self.digest = None
    
    @property
    def info(self):
        # pull datastream profile information from Fedora, but only when accessed
        if self._info is None:
            if self.obj._create:
                self._info = self._bootstrap_info()
            else:
                self._info = self.obj.getDatastreamProfile(self.id)
            if not self.versionable:
                self._info_backup = { 'dsLabel': self._info.label,
                                      'mimeType': self._info.mimetype,
                                      'versionable': self._info.versionable,
                                      'dsState': self._info.state,
                                      'formatURI': self._info.format,
                                      'checksumType': self._info.checksum_type,
                                      'checksum': self._info.checksum }
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
            if self.obj._create:
                self._content = self._bootstrap_content()
            else:
                data, url = self.obj.api.getDatastreamDissemination(self.obj.pid, self.id)
                self._content = self._convert_content(data, url)
                if not self.versionable:   
                    self._content_backup = data
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
        self.info.modified = True
    format = property(_get_format, _set_format, "datastream format URI")

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
            # FIXME: should be able to handle checksums
        # NOTE: as of Fedora 3.2, updating content without specifying mimetype fails (Fedora bug?)
        if 'mimeType' not in modify_opts.keys():
            # if datastreamProfile has not been pulled from fedora, use configured default mimetype
            if self._info is not None:
                modify_opts['mimeType'] = self.mimetype
            else:
                modify_opts['mimeType'] = self.defaults['mimetype']
            
        success, msg = self.obj.api.modifyDatastream(self.obj.pid, self.id, content=data,
                logMessage=logmessage, **modify_opts) 
        if success:
            # update modification indicators
            self.info_modified = False
            self.digest = self._content_digest()
            
        return success      # msg ?

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
            return self.obj.api.purgeDatastream(self.obj.pid, self.id, datetime_to_fedoratime(last_save),
                                                logMessage=logMessage)
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
    # FIXME: override _set_content to handle setting content?

    def _convert_content(self, data, url):
        return parse_rdf(data, url)

    def _bootstrap_content(self):
        return RdfGraph()

    def _content_as_node(self):
        graph = self.content
        data = graph.serialize()
        obj = xmlmap.load_xmlobject_from_string(data)
        return obj.node


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
        self.pid = pid
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
            self.pid = self._getDefaultPid()
            create = True

        self._create = bool(create)

        if create:
            self._init_as_new_object()

    def _init_as_new_object(self):
        for cmodel in getattr(self, 'CONTENT_MODELS', ()):
            self.rels_ext.content.add((URIRef(self.uri), URIRef(URI_HAS_MODEL),
                                       URIRef(cmodel)))

    def __str__(self):
        if self._create:
            return self.pid + ' (uningested)'
        else:
            return self.pid

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, str(self))

    def _getDefaultPid(self, namespace=None):
        kwargs = {}
        if namespace is not None:
            kwargs['namespace'] = namespace
        data, url = self.api.getNextPID(**kwargs)
        nextpids = parse_xml_object(NewPids, data, url)
        return nextpids.pids[0]

    @property
    def uri(self):
        "Fedora URI for this object (info:fedora/foo:### form of object pid) "
        return 'info:fedora/' + self.pid

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
        self.info_modified = True
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

    def getDatastreamProfile(self, dsid):
        """Get information about a particular datastream belonging to this object.

        :param dsid: datastream id
        :rtype: :class:`DatastreamProfile`
        """
        # NOTE: used by DatastreamObject
        data, url = self.api.getDatastream(self.pid, dsid)
        return parse_xml_object(DatastreamProfile, data, url)

    @property
    def history(self):
        if self._history is None:
            self.getHistory()
        return self._history

    def getHistory(self):
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
            self._ingest(logMessage)
        else:
            self._save_existing(logMessage)

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
        data, url = self.api.listMethods(self.pid)
        methods = parse_xml_object(ObjectMethods, data, url)
        self._methods = {}
        for sdef in methods.service_definitions:
            self._methods[sdef.pid] = sdef.methods
        return self._methods

    def getDissemination(self, service_pid, method, params={}):
        return self.api.getDissemination(self.pid, service_pid, method, method_params=params)

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
        # FIXME: make this work for new objects
        obj_is_literal = True
        if isinstance(object, DigitalObject):
            object = object.uri
            obj_is_literal = False
        elif isinstance(object, str) and object.startswith('info:fedora/'):
            obj_is_literal = False

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
            
        st = (URIRef(self.uri), URIRef(URI_HAS_MODEL), URIRef(model))
        return st in rels


class ContentModel(DigitalObject):
    """Fedora CModel object"""

    CONTENT_MODELS = ['info:fedora/fedora-system:ContentModel-3.0']
    ds_composite_model = XmlDatastream('DS-COMPOSITE-MODEL',
            'Datastream Composite Model', DsCompositeModel, defaults={
                'control_group': 'X',
                'versionable': True,
            })


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
        
