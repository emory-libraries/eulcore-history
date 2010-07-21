from eulcore import xmlmap

# FIXME: DateField still needs significant improvements before we can make
# it part of the real xmlmap interface.
from eulcore.xmlmap.fields import DateField
from eulcore.xmlmap.fields import Field, SingleNodeManager, NodeMapper

from eulcore.fedora.util import datetime_to_fedoratime, fedoratime_to_datetime

class FedoraDateMapper(xmlmap.fields.DateMapper):
    def to_python(self, node):
        rep = self.XPATH(node)
        return fedoratime_to_datetime(rep)

    def to_xml(self, dt):
        return datetime_to_fedoratime(dt)

class FedoraDateField(xmlmap.fields.Field):
    """Map an XPath expression to a single Python `datetime.datetime`.
    Assumes date-time format in use by Fedora, e.g. 2010-05-20T18:42:52.766Z
    """
    def __init__(self, xpath):
        super(FedoraDateField, self).__init__(xpath,
                manager = xmlmap.fields.SingleNodeManager(),
                mapper = FedoraDateMapper())

class FedoraDateListField(xmlmap.fields.Field):
    """Map an XPath expression to a list of Python `datetime.datetime`.
    Assumes date-time format in use by Fedora, e.g. 2010-05-20T18:42:52.766Z.
    If the XPath expression evaluates to an empty NodeList, evaluates to
    an empty list."""

    def __init__(self, xpath):
        super(FedoraDateListField, self).__init__(xpath,
                manager = xmlmap.fields.NodeListManager(),
                mapper = FedoraDateMapper())


# xml objects to wrap around xml returns from fedora

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
    """:class:`~eulcore.xmlmap.XmlObject` for object profile information
        returned by :meth:`REST_API.getObjectProfile`."""

    ROOT_NAME = 'objectProfile'

    label = xmlmap.StringField('objLabel')
    "object label"
    owner = xmlmap.StringField('objOwnerId')
    "object owner"
    created = FedoraDateField('objCreateDate')    
    "date the object was created"
    modified = FedoraDateField('objLastModDate')   
    "date the object was last modified"
    # do we care about these? probably not useful in this context...
    # - disseminator index view url
    # - object item index view url
    state = xmlmap.StringField('objState')
    "object state (A/I/D - Active, Inactive, Deleted)"

class ObjectHistory(xmlmap.XmlObject):
    ROOT_NAME = 'fedoraObjectHistory'
    pid = xmlmap.StringField('@pid')
    changed = FedoraDateListField('objectChangeDate')

class ObjectMethodService(xmlmap.XmlObject):
    ROOT_NAME = 'sDef'
    pid = xmlmap.StringField('@pid')
    methods = xmlmap.StringListField('method/@name')

class ObjectMethods(xmlmap.XmlObject):
    ROOT_NAME = 'objectMethods'
    service_definitions = xmlmap.NodeListField('sDef', ObjectMethodService)

class DatastreamProfile(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for datastream profile information
    returned by  :meth:`REST_API.getDatastream`."""

    ROOT_NAME = 'datastreamProfile'

    label = xmlmap.StringField('dsLabel')
    "datastream label"
    version_id = xmlmap.StringField('dsVersionID')
    "current datastream version id"
    created = FedoraDateField('dsCreateDate') 
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
    :meth:`REST_API.getNextPID`."""

    pids = xmlmap.StringListField('pid')


class RepositoryDescriptionPid(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for PID section of :class:`RepositoryDescription`"""
    namespace = xmlmap.StringField('PID-namespaceIdentifier')
    "PID namespace"
    delimiter = xmlmap.StringField('PID-delimiter')
    "PID delimiter"
    sample = xmlmap.StringField('PID-sample')
    "sample PID"
    retain_pids = xmlmap.StringField('retainPID')
    "list of pid namespaces configured to be retained"

class RepositoryDescriptionOAI(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for OAI section of :class:`RepositoryDescription`"""
    namespace = xmlmap.StringField('OAI-namespaceIdentifier')
    "OAI namespace"
    delimiter = xmlmap.StringField('OAI-delimiter')
    "OAI delimiter"
    sample = xmlmap.StringField('OAI-sample')
    "sample OAI id"

class RepositoryDescription(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for a repository description as returned
        by :meth:`API_A_LITE.describeRepository` """
    name = xmlmap.StringField('repositoryName')
    "repository name"
    base_url = xmlmap.StringField('repositoryBaseURL')
    "base url"
    version = xmlmap.StringField('repositoryVersion')
    "version of Fedora being run"
    pid_info = xmlmap.NodeField('repositoryPID', RepositoryDescriptionPid)
    ":class:`RepositoryDescriptionPid` - configuration info for pids"
    oai_info = xmlmap.NodeField('repositoryPID', RepositoryDescriptionOAI)
    ":class:`RepositoryDescriptionOAI` - configuration info for OAI"
    search_url = xmlmap.StringField('sampleSearch-URL')
    "sample search url"
    access_url = xmlmap.StringField('sampleAccess-URL')
    "sample access url"
    oai_url = xmlmap.StringField('sampleOAI-URL')
    "sample OAI url"
    admin_email = xmlmap.StringListField("adminEmail")
    "administrator emails"

class SearchResult(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for a single entry in the results
        returned by :meth:`REST_API.findObjects`"""
    def __init__(self, node, context=None):
        if context is None:
            context = {'namespaces' : {'res': 'http://www.fedora.info/definitions/1/0/types/'}}
        xmlmap.XmlObject.__init__(self, node, context)

    pid = xmlmap.StringField('res:pid')
    "pid"

class SearchResults(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for the results returned by
        :meth:`REST_API.findObjects`"""
    def __init__(self, node, context=None):
        if context is None:
            context = {'namespaces' : {'res': 'http://www.fedora.info/definitions/1/0/types/'}}
        xmlmap.XmlObject.__init__(self, node, context)

    session_token = xmlmap.StringField('res:listSession/res:token')
    "session token"
    cursor = xmlmap.IntegerField('res:listSession/res:cursor')
    "session cursor"
    expiration_date = DateField('res:listSession/res:expirationDate')
    "session experation date"
    results = xmlmap.NodeListField('res:resultList/res:objectFields', SearchResult)
    "search results - list of :class:`SearchResult`"

DS_NAMESPACE = 'info:fedora/fedora-system:def/dsCompositeModel#'
DS_NAMESPACES = { 'ds': DS_NAMESPACE }

class DsTypeModel(xmlmap.XmlObject):
    ROOT_NAMESPACES = DS_NAMESPACES

    id = xmlmap.StringField('@ID')
    mimetype = xmlmap.StringField('ds:form/@MIME')
    format_uri = xmlmap.StringField('ds:form/@FORMAT_URI')


class DsCompositeModel(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for a
    :class:`~eulcore.fedora.models.ContentModel`'s DS-COMPOSITE-MODEL
    datastream"""

    ROOT_NAME = 'dsCompositeModel'
    ROOT_NS = 'info:fedora/fedora-system:def/dsCompositeModel#'
    ROOT_NAMESPACES = DS_NAMESPACES

    # TODO: this feels like it could be generalized into a dict-like field
    # class.
    TYPE_MODEL_XPATH = 'ds:dsTypeModel[@ID=$dsid]'
    def get_type_model(self, dsid, create=False):
            field = Field(self.TYPE_MODEL_XPATH,
                        manager=SingleNodeManager(instantiate_on_get=create),
                        mapper=NodeMapper(DsTypeModel))
            context = { 'namespaces': DS_NAMESPACES,
                        'dsid': dsid }
            return field.get_for_node(self.node, context)
