import hashlib
from eulcore import xmlmap
from eulcore.xmlmap.core import XmlObject
from eulcore.fedora.util import parse_xml_object

class DatastreamProfile(xmlmap.XmlObject):
    label = xmlmap.StringField('dsLabel')
    version_id = xmlmap.StringField('dsVersionID')
    created = xmlmap.StringField('dsCreateDate')
    state = xmlmap.StringField('dsState')
    mimetype = xmlmap.StringField('dsMIME')
    format = xmlmap.StringField('dsFormatURI')
    control_group = xmlmap.StringField('dsControlGroup')
    size = xmlmap.IntegerField('dsSize')    # not reliable for managed datastreams as of Fedora 3.3
    versionable = xmlmap.SimpleBooleanField('dsVersionable', 'true', 'false')
    # infoType ?
    # location ?
    checksum_type = xmlmap.StringField('dsChecksumType')
    checksum = xmlmap.StringField('dsChecksum')

class DigitalObject(object):
    # NOTE: to be consolidated with other version of  Digital Object
    def __init__(self):
        self.dscache = {}       # accessed by DatastreamDescriptor to store and cache datastreams

    def getDatastreamProfile(self, dsid):
        data, url = self.api.getDatastream(self.pid, dsid)
        return parse_xml_object(DatastreamProfile, data, url)
    

class DatastreamObject(object):
    
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
        
        :rtype boolean:
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

    label = property(_get_label, _set_label)    
    mimetype = property(_get_mimetype, _set_mimetype)
    versionable = property(_get_versionable, _set_versionable)  
    state = property(_get_state, _set_state)
    format = property(_get_format, _set_format)

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

        :rtype boolean: success
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
    
class DatastreamDescriptor(object):
    
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
