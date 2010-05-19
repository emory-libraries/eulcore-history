import hashlib
import rdflib
from cStringIO import StringIO
from rdflib.Graph import Graph as RdfGraph

from Ft.Xml.Domlette import CanonicalPrint, PrettyPrint, \
        implementation as DomImplementation

from eulcore import xmlmap
from eulcore.fedora.api import ApiFacade
from eulcore.fedora.util import parse_xml_object, parse_rdf, RequestFailed
from eulcore.fedora.xml import ObjectDatastream, ObjectDatastreams, \
        ObjectProfile, DatastreamProfile, NewPids

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
                self._content = self._convert_content(self.obj.api.getDatastreamDissemination(self.obj.pid, self.id))
                # calculate and store a digest of the current datastream text content
                self.digest = self._content_digest()
            else:
                self._content = self._bootstrap_content()
        return self._content
    def _set_content(self, val):
        self._content = val
    content = property(_get_content, _set_content, None, "datastream content")

    def _convert_content(self, content):
        # convert the raw API output of getDatastreamDissemination into the expected content type
        data, url = content
        return data

    def _bootstrap_content(self):
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
        # NOTE: as of Fedora 3.2, updating content without specifying mimetype fails (Fedora bug?)
        if 'mimeType' not in modify_opts.keys():
            # if datastreamProfile has not been pulled from fedora, use configured default mimetype
            if self._info is not None:
                modify_opts['mimeType'] = self.mimetype
            else:
                modify_opts['mimeType'] = self.defaults['mimetype']
            
        success, msg = self.obj.api.modifyDatastream(self.obj.pid, self.id, content=data,
                logMessage=logmessage, **modify_opts)    # checksums?
        if success:
            # update modification indicators
            self.info_modified = False
            self.digest = self._content_digest()
            
        return success      # msg ?
    
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

    def _convert_content(self, content):
        data, url = content
        return parse_xml_object(self.objtype, data, url)

    def _bootstrap_content(self):
        return self.objtype()


class XmlDatastream(Datastream):
    """XML-specific version of :class:`Datastream`.

    Datastreams are initialized as instances of :class:`XmlDatastreamObject`.
    Additional, optional parameter ``objtype`` is passed to the Datastream object
    configure the type of  :class:`eulcore.xmlmap.XmlObject` that should be returned.
    """
    _datastreamClass = XmlDatastreamObject
    
    def __init__(self, id, label, objtype=None, defaults={}):        
        super(XmlDatastream, self).__init__(id, label, defaults)
        self.datastream_args['objtype'] = objtype


class RdfDatastreamObject(DatastreamObject):
    """Extends :class:`DatastreamObject` in order to initialize datastream content
    as an RDF graph.
    """
    default_mimetype = "application/xml+rdf"
    # FIXME: override _set_content to handle setting content?

    def _convert_content(self, content):
        data, url = content
        return parse_rdf(data, url)

    def _bootstrap_content(self):
        return RdfGraph()


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
        profile or any datastream content or info).        
        """
        if callable(self.pid):
            self._ingest(logMessage)
        else:
            self._save_existing(logMessage)

    def _save_existing(self, logMessage):
        # TODO: add logic to back out changes if a failure occurs part-way through saving

        # loop through any datastreams that have been accessed, saving any that have been modified
        for dsobj in self.dscache.itervalues():
            if dsobj.isModified():
                if not dsobj.save(logMessage):
                    raise Exception("Error saving %s/%s" % (self.pid, dsobj.id))

        # only save object profile after all modified datastreams have been successfully saved
        if self.info_modified:
            if not self.saveProfile(logMessage):
                raise Exception("Error saving object profile for %s" % self.pid)

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
            if not isinstance(fval, XmlDatastream):
                continue
            ds = fval

            dsobj = getattr(self, fname) # get it again to go through __get__
            if dsobj.control_group != 'X':
                continue # FIXME: only inline xml for now

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

            orig_content_xml = dsobj.content.dom_node
            content_xml = doc.importNode(orig_content_xml, True)
            content_container_xml.appendChild(content_xml)

        sio = StringIO()
        if pretty: # for easier debug
            PrettyPrint(doc, stream=sio)
        else:
            CanonicalPrint(doc, stream=sio)

        return sio.getvalue()

    def get_datastreams(self):
        """
        Get all datastreams that belong to this object.

        Returns a dictionary; key is datastream id, value is an :class:`ObjectDatastream`
        for that datastream.

        :rtype: dictionary
        """
        if self._ingested:
            # FIXME: add caching? make a property?
            data, url = self.api.listDatastreams(self.pid)
            dsobj = parse_xml_object(ObjectDatastreams, data, url)
            return dict([ (ds.dsid, ds) for ds in dsobj.datastreams ])
        else:
            # FIXME: should we default to the datastreams defined in code?
            return {}


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
            ds_list = self.get_datastreams()
            if "RELS-EXT" not in ds_list.keys():
                return False
            else:
                raise Exception(e)            
            
        st = (rdflib.URIRef(self.uri), rdflib.URIRef(URI_HAS_MODEL), rdflib.URIRef(model))
        return st in rels
