from datetime import datetime
from dateutil.tz import tzutc
import hashlib
import rdflib
from cStringIO import StringIO
from rdflib.Graph import Graph as RdfGraph

from Ft.Xml.Domlette import CanonicalPrint, PrettyPrint, \
        implementation as DomImplementation

from eulcore import xmlmap
from eulcore.fedora.util import parse_xml_object, parse_rdf, RequestFailed, fedora_time_format
from eulcore.fedora.xml import ObjectDatastreams, ObjectProfile, DatastreamProfile, NewPids

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
            if self.obj._ingested:
                self._info = self.obj.getDatastreamProfile(self.id)
            else:
                self._info = self._bootstrap_info()
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
            if self.obj._ingested:
                data, url = self.obj.api.getDatastreamDissemination(self.obj.pid, self.id)
                self._content = self._convert_content(data, url)
                if not self.versionable:   
                    self._content_backup = data
                # calculate and store a digest of the current datastream text content
                self.digest = self._content_digest()
            else:
                self._content = self._bootstrap_content()
        return self._content
    def _set_content(self, val):
        # if datastream is not versionable, grab contents before updating
        if not self.versionable:
            self._get_content()
        self._content = val
    content = property(_get_content, _set_content, None, "datastream content")

    def _convert_content(self, data, url):
        # convert output of getDatastreamDissemination into the expected content type
        return data

    def _bootstrap_content(self):
        return None

    def _content_as_dom(self):
        # used for serializing inline xml datastreams at ingest
        return None

    def isModified(self):
        """Check if either the datastream content or profile fields have changed
        and should be saved to Fedora.
        
        :rtype: boolean
        """
        return self.info_modified or self._content_digest() != self.digest

    def _content_digest(self):
        # generate a hash of the content so we can easily check if it has changed and should be saved
        return hashlib.sha1(self._content_as_text()).hexdigest()

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
    mimetype = property(_get_mimetype, _set_mimetype, None, "mimetype for the datastream")

    def _get_versionable(self):
        return self.info.versionable
    def _set_versionable(self, val):
        self.info.versionable = val
        self.info_modified = True
    versionable = property(_get_versionable, _set_versionable, None, "boolean; is the datastream versioned")

    def _get_state(self):
        return self.info.state
    def _set_state(self, val):
        self.info.state = val
        self.info_modified = True
    state = property(_get_state, _set_state, None, "datastream state (A/I/D)")

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

    def _content_as_text(self):
        # return datastream content as text
        if hasattr(self.content, 'serialize'):
            return self.content.serialize()
        else:
            return str(self.content)
    
    def save(self, logmessage=None):
        """Save datastream content and any changed datastream profile
        information to Fedora.

        :rtype: boolean for success
        """
        data = self._content_as_text()
        
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

    def undo_last_save(self, datetime, logMessage=None):
        """Undo the last change made to the datastream content and profile, effectively 
        reverting to the object state in Fedora as of the specified timestamp.

        For a versioned datastream, this will purge all datastream versions newer
        than the specified time.  For an unversioned datastream, this will overwrite
        the last changes with a cached version of any content and/or info pulled
        from Fedora.
        """
        
        # NOTE: currently not clearing any of the object caches and backups
        # of fedora content and datastream info, as it is unclear what (if anything)
        # should be cleared

        if self.versionable:
            # if this is a versioned datastream, Fedora handles it for us;
            # simply purge any revisions after the specified time
            return self.obj.api.purgeDatastream(self.obj.pid, self.id, fedora_time_format(datetime),
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
    """Datastream descriptor to make it easy to configure datastreams that belong
    to a particular :class:`DigitalObject`.

    When accessed, will initialize a :class:`DatastreamObject` and cache it on
    the :class:`DigitalObject` that it belongs to.

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
    as an :class:`eulcore.xmlmap.XmlObject`.

    See :class:`DigitalObject` for more details.  Has one additional parameter:

    :param objtype: xml object type to use for datastream content; if not specified,
        defaults to :class:`eulcore.xmlmap.XmlObject`
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

    def _content_as_dom(self):
        return self.content.dom_node


class XmlDatastream(Datastream):
    """XML-specific version of :class:`Datastream`.

    Datastreams are initialized as instances of :class:`XmlDatastreamObject`.
    An dditional, optional parameter ``objtype`` is passed to the Datastream object
    to configure the type of  :class:`eulcore.xmlmap.XmlObject` that should be
    used for datastream content.
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

    def _content_as_dom(self):
        graph = self.content
        data = graph.serialize()
        obj = xmlmap.load_xmlobject_from_string(data)
        return obj.dom_node


class RdfDatastream(Datastream):
    """RDF-specific version of :class:`Datastream`.

    Datastreams are initialized as instances of :class:`RdfDatastreamObject`.
    """
    _datastreamClass = RdfDatastreamObject


class DigitalObject(object):
    """
    A single digital object in a Fedora respository, with methods for accessing
    the parts of that object.
    """

    # TODO: add once we fully support inheriting datastreams:
    #dc = XmlDatastream("DC", "Dublin Core", DublinCore)
    #rels_ext = RdfDatastream("RELS-EXT", "External Relations")

    def __init__(self, api, pid=None):
        self.api = api
        self.dscache = {}       # accessed by DatastreamDescriptor to store and cache datastreams

        # cache object profile, track if it is modified and needs to be saved
        self._info = None
        self.info_modified = False
        
        # datastream list from fedora
        self._ds_list = None

        # a string pid is a live object in the repository. a callable pid
        # means a new object: we call that function to get our initial pid.
        # None is a new object, and use a default pid generation function.
        if pid is None:
            pid = self._getDefaultPid
        self.pid = pid

    def __str__(self):
        return self.pid

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.pid)

    @property
    def _ingested(self):
        # as mentioned in __init__, a string pid is pulled from the repo. a
        # callable pid is not yet ingested: we'll call that function to get
        # the pid at ingest
        return not callable(self.pid)

    def _getDefaultPid(self, namespace=None):
        kwargs = {}
        if namespace is not None:
            kwargs['namespace'] = namespace
        data, url = self.api.getNextPID(**kwargs)
        nextpids = parse_xml_object(NewPids, data, url)
        return nextpids.pids[0]

    @property
    def uri(self):
        "Fedora URI for this object (info:fedora form of object pid) "
        if self._ingested:
            return 'info:fedora/' + self.pid
        # otherwise we don't have a uri yet

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
    state = property(_get_state, _set_state, None, "object state (A/I/D)")

    # read-only info properties
    @property       
    def created(self):
        return self.info.created

    @property
    def modified(self):
        return self.info.modified

    def getDatastreamProfile(self, dsid):
        """Get information about a particular datastream on this object.

        :param dsid: datastream id
        :rtype: :class:`DatastreamProfile`
        """
        data, url = self.api.getDatastream(self.pid, dsid)
        return parse_xml_object(DatastreamProfile, data, url)

    def getProfile(self):
        """Get information about this object (label, owner, created, etc.).

        :rtype: :class:`ObjectProfile`
        """
        if self._ingested:
            data, url = self.api.getObjectProfile(self.pid)
            return parse_xml_object(ObjectProfile, data, url)
        else:
            return ObjectProfile()

    def saveProfile(self, logMessage=None):
        if not self._ingested:
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
        """
        # TODO: update docstring to indicate what happens for a new object?
        if callable(self.pid):
            self._ingest(logMessage)
        else:
            self._save_existing(logMessage)

    def _save_existing(self, logMessage):
        # save an object that has already been ingested into fedora

        # pre-save setup, so we can recover if something goes wrong:
        # - record checkpoint time before saving, for backing out changes
        save_start = datetime.now(tzutc())
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
                cleaned = self._undo_save(saved, save_start,
                                          "failed saving %s, rolling back out to %s" % \
                                           (ds, save_start))
                raise DigitalObjectSaveFailure(self.pid, ds, to_save, saved, cleaned)

        # NOTE: to_save list in exception will never include profile; should it?

        # FIXME: catch exceptions on save, treat same as failure to save (?)

        # save object profile (if needed) after all modified datastreams have been successfully saved
        if self.info_modified:
            if not self.saveProfile(logMessage):
                cleaned = self._undo_save(saved, save_start)
                raise DigitalObjectSaveFailure(self.pid, "object profile", to_save, saved, cleaned)

    def _undo_save(self, datastreams, save_start, logMessage=None):
        """Takes a list of datastreams and a datetime, run undo save on all of them,
        and returns a list of the datastreams where the undo succeeded.

        :param datastreams: list of datastream ids (should be in self.dscache)
        :param save_start: datetime to use for datastream undo save rollback
        """
        return [ds for ds in datastreams if self.dscache[ds].undo_last_save(save_start, logMessage)]

    def _ingest(self, logMessage):
        requested_pid = self.pid()
        foxml = self._build_foxml_for_ingest(requested_pid)
        returned_pid = self.api.ingest(foxml, logMessage)

        if returned_pid != requested_pid:
            msg = ('fedora returned unexpected pid "%s" when trying to ' + 
                   'ingest object with pid "%s"') % \
                  (returned_pid, requested_pid)
            raise Exception(msg)

        # then clean up the local object so that self knows it's dealing
        # with an ingested object now
        self.pid = returned_pid
        self._info = None
        self.info_modified = False
        self.dscache = {}

    def _build_foxml_for_ingest(self, pid, pretty=False):
        FOXML_NS = "info:fedora/fedora-system:def/foxml#"
        doc = DomImplementation.createDocument(FOXML_NS, 'foxml:digitalObject', None)
        obj = doc.documentElement
        obj.setAttributeNS(None, 'VERSION', '1.1')
        obj.setAttributeNS(None, 'PID', pid)

        props = doc.createElementNS(FOXML_NS, 'foxml:objectProperties')
        obj.appendChild(props)

        state = doc.createElementNS(FOXML_NS, 'foxml:property')
        state.setAttributeNS(None, 'NAME', 'info:fedora/fedora-system:def/model#state')
        state.setAttributeNS(None, 'VALUE', self.state or 'A')
        props.appendChild(state)

        if self.label:
            label = doc.createElementNS(FOXML_NS, 'foxml:property')
            label.setAttributeNS(None, 'NAME', 'info:fedora/fedora-system:def/model#label')
            label.setAttributeNS(None, 'VALUE', self.label)
            props.appendChild(label)

        if self.owner:
            owner = doc.createElementNS(FOXML_NS, 'foxml:property')
            owner.setAttributeNS(None, 'NAME', 'info:fedora/fedora-system:def/model#ownerId')
            owner.setAttributeNS(None, 'VALUE', self.owner)
            props.appendChild(owner)

        # collect datastream definitions for ingest.
        # FIXME: this method of identifying datastreams doesn't address
        # inheritance.
        for fname, fval in self.__class__.__dict__.iteritems():
            if not isinstance(fval, Datastream):
                continue
            ds = fval

            dsobj = getattr(self, fname) # get it again to go through __get__
            if dsobj.control_group != 'X':
                continue # FIXME: only inline xml for now

            orig_content_dom = dsobj._content_as_dom()
            if not orig_content_dom:
                continue # can't include a ds that doesn't know how to dom itself

            ds_xml = doc.createElementNS(FOXML_NS, 'foxml:datastream')
            ds_xml.setAttributeNS(None, 'ID', ds.id)
            ds_xml.setAttributeNS(None, 'CONTROL_GROUP', dsobj.control_group)
            ds_xml.setAttributeNS(None, 'STATE', dsobj.state)
            ds_xml.setAttributeNS(None, 'VERSIONABLE',
                    str(dsobj.versionable).lower())
            obj.appendChild(ds_xml)

            ver_xml = doc.createElementNS(FOXML_NS, 'foxml:datastreamVersion')
            ver_xml.setAttributeNS(None, 'ID', ds.id + '.0')
            ver_xml.setAttributeNS(None, 'MIMETYPE', dsobj.mimetype)
            if dsobj.format:
                ver_xml.setAttributeNS(None, 'FORMAT_URI', dsobj.format)
            if dsobj.label:
                ver_xml.setAttributeNS(None, 'LABEL', dsobj.label)
            ds_xml.appendChild(ver_xml)

            content_container_xml = doc.createElementNS(FOXML_NS, 'foxml:xmlContent')
            ver_xml.appendChild(content_container_xml)

            content_xml = doc.importNode(orig_content_dom, True)
            content_container_xml.appendChild(content_xml)

        sio = StringIO()
        if pretty: # for easier debug
            PrettyPrint(doc, stream=sio)
        else:
            CanonicalPrint(doc, stream=sio)

        return sio.getvalue()

    def _get_datastreams(self):
        """
        Get all datastreams that belong to this object.

        Returns a dictionary; key is datastream id, value is an :class:`ObjectDatastream`
        for that datastream.

        :rtype: dictionary
        """
        if self._ingested:
            # NOTE: can be accessed as a cached class property via ds_list
            data, url = self.api.listDatastreams(self.pid)
            dsobj = parse_xml_object(ObjectDatastreams, data, url)
            return dict([ (ds.dsid, ds) for ds in dsobj.datastreams ])
        else:
            # FIXME: should we default to the datastreams defined in code?
            return {}

    @property
    def ds_list(self):      # NOTE: how to name to distinguish from locally configured datastream objects?
        """
        Dictionary of all datastreams that belong to this object in Fedora.
        Key is datastream id, value is an :class:`ObjectDatastream` for that
        datastream.
        """
        if self._ds_list is None:
            self._ds_list = self._get_datastreams()
        return self._ds_list

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
            
        st = (rdflib.URIRef(self.uri), rdflib.URIRef(URI_HAS_MODEL), rdflib.URIRef(model))
        return st in rels


class DigitalObjectSaveFailure(StandardError):
    """Custom exception class for when a save error occurs part-way through saving 
    an instance of :class:`DigitalObject`.  This exception should contain enough
    information to determine where the save failed, and whether or not any changes
    saved before the failure were successfully rolled back.

    These properties are available:
     * obj_pid - pid of the :class:`DigitalObject` instance that failed to save
     * failure - where the failure occurred (either a datastream ID or 'object profile')
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
        
