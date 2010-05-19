from eulcore import xmlmap

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
    ROOT_NAME = 'objectProfile'

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

class NewPids(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for a list of pids as returned by
    Fedora REST API."""

    pids = xmlmap.StringListField('pid')
