import hashlib
from eulcore import xmlmap
from eulcore.xmlmap.core import XmlObject
from eulcore.fedora.util import parse_xml_object

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


class DigitalObject(object):
    # NOTE: to be consolidated with other version of  Digital Object
    
    def __init__(self):
        self.dscache = {}       # accessed by DatastreamDescriptor to store and cache datastreams

    def getDatastreamProfile(self, dsid):
        """Get information about a particular datastream on this object.
        
        :rtype: :class:`DatastreamProfile`
        """
        data, url = self.api.getDatastream(self.pid, dsid)
        return parse_xml_object(DatastreamProfile, data, url)
    

class DatastreamObject(object):
    """Object to easy accessing and updating a datastream belonging to a Fedora object.

    Intended to be used with :class:`DigitalObject` and intialized
    via :class:`Datastream`.

    Initialization parameters:
        :param obj: the :class:`DigitalObject` that this datastream belongs to.
        :param id: datastream id
        :param label: default datastream label
        :param content: contents of the datastream; currently handles text or XmlObject
        :param mimetype: default datastream mimetype
        :param versionable: default configuration for datastream versioning
        :param state: default configuration for datastream state
        :param format: default configuration for datastream format URI
    """
    def __init__(self, obj, id, label, content=None, mimetype="text/xml", versionable=False,
        state="A", format=None):
        self.obj = obj
        self.id = id
        self.content = content
        self.defaults = {'label': label, 'mimetype': mimetype, 'versionable' : versionable,
            'state' : state, 'format': format}
        self._info = None

        self.info_modified = False
        # calculate and store a digest of the current datastream text content
        self.digest = self._content_digest()
    
    @property
    def info(self):
        # pull datastream profile information from Fedora, but only when accessed
        if self._info is None:
            self._info = self.obj.getDatastreamProfile(self.id)
        return self._info

    def isModified(self):
        """Check if either the datastream content or profile fields have changed
        and should be saved to Fedora.
        
        :rtype: boolean
        """
        return self.info_modified or self._content_digest() != self.digest

    def _content_digest(self):
        # generate a hash of the content so we can easily check if it has changed and should be changed
        return hashlib.sha1(self._content_as_text()).hexdigest()

    ### access to datastream profile fields; tracks if changes are made for saving to Fedora

    def _get_label(self):
        return self.info.label

    def _set_label(self, val):
        self.info.label = val
        self.info_modified = True    
    
    def _get_mimetype(self):
        return self.info.mimetype
    
    def _set_mimetype(self, val):
        self.info.mimetype = val
        self.info_modified = True

    def _get_versionable(self):
        return self.info.versionable

    def _set_versionable(self, val):
        self.info.versionable = val
        self.info_modified = True

    def _get_state(self):
        return self.info.state

    def _set_state(self, val):
        self.info.state = val
        self.info_modified = True

    def _get_format(self):
        return self.info.format

    def _set_format(self, val):
        self.info.format = val
        self.info.modified = True

    label = property(_get_label, _set_label, None, "datastream label")
    mimetype = property(_get_mimetype, _set_mimetype, None, "mimetype for the datastream")
    versionable = property(_get_versionable, _set_versionable, None, "boolean; is the datastream versioned")
    state = property(_get_state, _set_state, None, "datastream state (A/I/D)")
    format = property(_get_format, _set_format, "datastream format URI")

    @property       # read-only info property
    def control_group(self):
        return self.info.control_group

    def _content_as_text(self):
        # return datastream content as text
        if isinstance(self.content, XmlObject):
            return self.content.serialize()
        else:
            return self.content
    
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
    the :class:`DigitalObject` that it belongs to.  If an object type is specified,
    the datastream contents will be initialized as an
    :class:`eulcore.xmlmap.core.XmlObject` and made accessible as the content of
    the :class:`DatastreamObject`.  Otherwise, the content will be available
    exactly as it was returned to Fedora.

    All other configuration defaults are passed on to the :class:`DatastreamObject`.
    """
    
    def __init__(self, id, label, objtype=None, defaults={}):
        self.datastream = None
        self.id = id
        self.label = label
        self.objtype = objtype   # optional, returns content as-is if not specified
        self.datastream_defaults = defaults

    def __get__(self, obj, objtype): 
        if obj is None:
            return self
        if not self.id in obj.dscache.keys() or obj.dscache[self.id] is None:
            data, url = obj.api.getDatastreamDissemination(obj.pid, self.id)
            if self.objtype:
                ds_content = parse_xml_object(self.objtype, data, url)
            else:
                ds_content = data
            obj.dscache[self.id] = DatastreamObject(obj, self.id, self.label,
                ds_content, **self.datastream_defaults)
        return obj.dscache[self.id]
    
    # set and delete not implemented on datastream descriptor
    # - delete would only make sense for optional datastreams, not yet needed
    # - saving updated content to fedora handled by datastream object
