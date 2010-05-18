import hashlib
import rdflib

from eulcore import xmlmap
from eulcore.fedora.api import ApiFacade
from eulcore.fedora.util import parse_xml_object, parse_rdf, RequestFailed

# FIXME: needed by both server and models, where to put?
URI_HAS_MODEL = 'info:fedora/fedora-system:def/model#hasModel'

# xml objects to wrap around xml returns from fedora
# FIXME: where should these actually live?

class ObjectDatastream(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for a single datastream as returned
        by :meth:`REST_API.listDatastreams` """
    dsid = xmlmap.StringField('@dsid')
    "datastream id - `@dsid`"
    label = xmlmap.StringField('@label')
    "datastream label - `@label`"
    mimeType = xmlmap.StringField('@mimeType')
    "datastream mime type - `@mimeType`"

class ObjectDatastreams(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for the list of a single object's
        datastreams, as returned by  :meth:`REST_API.listDatastreams`"""
    pid = xmlmap.StringField('@pid')
    "object pid - `@pid`"
    datastreams = xmlmap.NodeListField('datastream', ObjectDatastream)
    "list of :class:`ObjectDatastream`"

class ObjectProfile(xmlmap.XmlObject):
    ":class:`xmlmap.XmlObject` for object profile information returned by Fedora REST API."
    label = xmlmap.StringField('objLabel')
    "object label"
    owner = xmlmap.StringField('objOwnerId')
    "object owner"
    created = xmlmap.StringField('objCreateDate')        # date?
    "date the object was created"
    modified = xmlmap.StringField('objLastModDate')        # date?
    "date the object was last modified"
    # do we care about these? probably not useful in this context...
    # - disseminator index view url
    # - object item index view url
    state = xmlmap.StringField('objState')
    "object state (A/I/D - Active, Inactive, Deleted)"

class DatastreamProfile(xmlmap.XmlObject):
    ":class:`xmlmap.XmlObject` for datastream profile information returned by Fedora REST API."
    label = xmlmap.StringField('dsLabel')
    "datastream label"
    version_id = xmlmap.StringField('dsVersionID')
    "current datastream version id"
    created = xmlmap.StringField('dsCreateDate')        # date?
    "date the datastream was created"
    state = xmlmap.StringField('dsState')
    "datastream state (A/I/D - Active, Inactive, Deleted)"
    mimetype = xmlmap.StringField('dsMIME')
    "datastream mimetype"
    format = xmlmap.StringField('dsFormatURI')
    "format URI for the datastream, if any"
    control_group = xmlmap.StringField('dsControlGroup')
    "datastream control group (inline XML, Managed, etc)"
    size = xmlmap.IntegerField('dsSize')    # not reliable for managed datastreams as of Fedora 3.3
    "integer; size of the datastream content"
    versionable = xmlmap.SimpleBooleanField('dsVersionable', 'true', 'false')
    "boolean; indicates whether or not the datastream is currently being versioned"
    # infoType ?
    # location ?
    checksum = xmlmap.StringField('dsChecksum')
    "checksum for current datastream contents"
    checksum_type = xmlmap.StringField('dsChecksumType')
    "type of checksum"

    
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
    default_mimetype = "text/xml"    # FIXME: reasonable default minetype for non-xml datastream/
    def __init__(self, obj, id, label, mimetype=None,
                 versionable=False, state="A", format=None):
                        
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
        }
        self._info = None
        self._content = None

        self.info_modified = False
        self.digest = None
    
    @property
    def info(self):
        # pull datastream profile information from Fedora, but only when accessed
        if self._info is None:
            self._info = self.obj.getDatastreamProfile(self.id)
        return self._info

    def _get_content(self):
        # pull datastream content from Fedora, but only when accessed
        if self._content is None:
            self._content = self._convert_content(self.obj.api.getDatastreamDissemination(self.obj.pid, self.id))
            # calculate and store a digest of the current datastream text content
            self.digest = self._content_digest()
        return self._content
    def _set_content(self, val):
        self._content = val
    content = property(_get_content, _set_content, None, "datastream content")

    def _convert_content(self, content):
        # convert the raw API output of getDatastreamDissemination into the expected content type
        data, url = content
        return data

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

    def __init__(self, pid=None, opener=None):
        self.pid = pid
        self.opener = opener
        self.dscache = {}       # accessed by DatastreamDescriptor to store and cache datastreams

        # cache object profile, track if it is modified and needs to be saved
        self._info = None
        self.info_modified = False

    def __str__(self):
        return self.pid

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.pid)

    @property
    def uri(self):
        "Fedora URI for this object (info:fedora form of object pid) "
        return 'info:fedora/' + self.pid

    @property
    def api(self):
        "instance of :class:`ApiFacade`, with the same fedora root url and credentials"
        return ApiFacade(self.opener)

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
        data, url = self.api.getObjectProfile(self.pid)
        return parse_xml_object(ObjectProfile, data, url)

    def saveProfile(self, logMessage=None):
        saved = self.api.modifyObject(self.pid, self.label, self.owner, self.state, logMessage)
        if saved:
            # profile info is no longer different than what is in Fedora
            self.info_modified = False
        return saved
    
    def save(self, logMessage=None):
        """Save to Fedora any parts of this object that have been modified (object
        profile or any datastream content or info).        
        """
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

    def get_datastreams(self):
        """
        Get all datastreams that belong to this object.

        Returns a dictionary; key is datastream id, value is an :class:`ObjectDatastream`
        for that datastream.

        :rtype: dictionary
        """
        # FIXME: add caching? make a property?
        data, url = self.api.listDatastreams(self.pid)
        dsobj = parse_xml_object(ObjectDatastreams, data, url)
        return dict([ (ds.dsid, ds) for ds in dsobj.datastreams ])


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


