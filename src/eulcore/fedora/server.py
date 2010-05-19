from urllib import urlencode
from Ft.Xml.XPath.Context import Context

from eulcore import xmlmap
from eulcore.fedora.api import HTTP_API_Base, ApiFacade
from eulcore.fedora.models import DigitalObject, URI_HAS_MODEL
# FIXME: should risearch be moved to apis?
from eulcore.fedora.util import RelativeOpener, parse_rdf, parse_xml_object

# FIXME: DateField still needs significant improvements before we can make
# it part of the real xmlmap interface.
from eulcore.xmlmap.fields import DateField

# a repository object, basically a handy facade for easy api access

class Repository(object):
    "Pythonic interface to a single Fedora Commons repository instance."
    
    def __init__(self, root, username=None, password=None):
        self.opener = RelativeOpener(root, username, password)
        self.api = ApiFacade(self.opener)
        self.fedora_root = root
        self.username = username
        self.password = password

    @property
    def risearch(self):
        "instance of :class:`ResourceIndex`, with the same root url and credentials"
        return ResourceIndex(self.opener)

    def get_next_pid(self, namespace=None, count=None):
        """
        Request next available pid or pids from Fedora, optionally in a specified
        namespace.  Calls :meth:`REST_API.getNextPID`.

        :param namespace: (optional) get the next pid in the specified pid namespace;
            otherwise, Fedora will return the next pid in the configured default namespace.
        :param count: (optional) get the specified number of pids; by default, returns 1 pid
        :rtype: string or list of strings
        """
        kwargs = {}
        if namespace:
            kwargs['namespace'] = namespace
        if count:
            kwargs['numPIDs'] = count
        data, url = self.api.getNextPID(**kwargs)
        nextpids = parse_xml_object(NewPids, data, url)

        if count is None:
            return nextpids.pids[0]
        else:
            return nextpids.pids


    def ingest(self, text, log_message=None):
        """
        Ingest a new object into Fedora. Returns the pid of the new object on
        success.  Calls :meth:`REST_API.ingest`.

        :param text: full text content of the object to be ingested
        :param log_message: optional log message
        :rtype: string
        """
        kwargs = { 'text': text }
        if log_message:
            kwargs['logMessage'] = log_message
        return self.api.ingest(**kwargs)

    def purge_object(self, pid, log_message=None):
        """
        Purge an object from Fedora.  Calls :meth:`REST_API.purgeObject`.

        :param pid: pid of the object to be purged
        :param log_message: optional log message
        """
        #FIXME/TODO: API-M returns timestamp on success; how do we indicate success here? (no return value)
        kwargs = { 'pid': pid }
        if log_message:
            kwargs['logMessage'] = log_message
        return self.api.purgeObject(**kwargs)

    def get_objects_with_cmodel(self, cmodel_uri, type=None):
        """
        Find objects in Fedora with the specified content model.

        :param cmodel_uri: content model URI (should be full URI in  info:fedora/pid:### format)
        :param type: type of object to return (e.g., {class:`DigitalObject`)
        :rtype: list of objects
        """
        uris = self.risearch.get_subjects(URI_HAS_MODEL, cmodel_uri)
        return [ self.get_object(uri, type) for uri in uris ]

    def get_object(self, pid, type=None):
        """
        Initialize a single object from Fedora.

        NOTE: currently does not actually access Fedora, just initializes a
        :class:`DigitalObject` with the same Fedora config & credentials

        :param pid: pid of the object to request
        :param type: type of object to return; defaults to :class:`DigitalObject`
        :rtype: single object of the type specified
        """
        # FIXME/TODO: use getObjectProfile or similar to get minimal info about the object
        if type is None:
            type = DigitalObject
        if pid.startswith('info:fedora/'): # passed a uri
            pid = pid[len('info:fedora/'):]
        return type(self.api, pid)

    def find_objects(self, type=None, chunksize=None, **kwargs):
        """
        Find objects in Fedora.  Find query should be generated via keyword args,
        based on the fields in Fedora documentation.  Find query currently uses
        a contains (~) search for all search terms.  Calls :meth:`REST_API.findObjects`.

        Example usage - search for all objects where the owner is 'jdoe'::
        
            repository.find_objects(ownerId='jdoe')

        :param type: type of objects to return; defaults to :class:`DigitalObject`
        :param chunksize: number of objects to return at a time
        :rtype: generator for list of objects
        """
        type = type or DigitalObject

        # FIXME: query production here is frankly sketchy
        query = ' '.join([ '%s~%s' % (k, v) for k, v in kwargs.iteritems() ])
        data, url = self.api.findObjects(query, chunksize=chunksize)
        chunk = parse_xml_object(SearchResults, data, url)
        while True:
            for result in chunk.results:
                yield type(self.api, result.pid)

            if chunk.session_token:
                data, url = self.api.findObjects(query, session_token=chunk.session_token, chunksize=chunksize)
                chunk = parse_xml_object(SearchResults, data, url)
            else:
                break


# xml objects to wrap around xml returns from fedora


class SearchResult(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for a single entry in the results
        returned by :meth:`REST_API.findObjects`"""
    def __init__(self, dom_node, context=None):
        if context is None:
            context = Context(dom_node, processorNss={'res': 'http://www.fedora.info/definitions/1/0/types/'})
        xmlmap.XmlObject.__init__(self, dom_node, context)

    pid = xmlmap.StringField('res:pid')

class SearchResults(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for the results returned by
        :meth:`REST_API.findObjects`"""
    def __init__(self, dom_node, context=None):
        if context is None:
            context = Context(dom_node, processorNss={'res': 'http://www.fedora.info/definitions/1/0/types/'})
        xmlmap.XmlObject.__init__(self, dom_node, context)

    session_token = xmlmap.StringField('res:listSession/res:token')
    cursor = xmlmap.IntegerField('res:listSession/res:cursor')
    expiration_date = DateField('res:listSession/res:expirationDate')
    results = xmlmap.NodeListField('res:resultList/res:objectFields', SearchResult)

class NewPids(xmlmap.XmlObject):
    pids = xmlmap.StringListField('pid')


# make it easy to access a DigitalObject as other types if it has the
# appropriate cmodel info.
# currently unused - not officially released
class ObjectTypeDescriptor(object):
    def __init__(self, model, objtype):
        self.model = model
        self.objtype = objtype

    def __get__(self, obj, objtype):
        try:
            if obj.has_model(self.model):
                return self.objtype(self.api, obj.pid)
        except:
            return None


class RepositoryDescriptionPid(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for PID section of :class:`RepositoryDescription`"""
    namespace = xmlmap.StringField('PID-namespaceIdentifier')
    delimiter = xmlmap.StringField('PID-delimiter')
    sample = xmlmap.StringField('PID-sample')
    retain_pids = xmlmap.StringField('retainPID')

class RepositoryDescriptionOAI(xmlmap.XmlObject):
    """:class:`~eulcore.xmlmap.XmlObject` for OAI section of :class:`RepositoryDescription`"""
    namespace = xmlmap.StringField('OAI-namespaceIdentifier')
    delimiter = xmlmap.StringField('OAI-delimiter')
    sample = xmlmap.StringField('OAI-sample')

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


class ResourceIndex(HTTP_API_Base):
    "Python object for accessing Fedora's Resource Index."

    def find_statements(self, spo_query):
        """
        Run an SPO (subject-predicate-object) query and return the results as RDF.

        :param spo_query: SPO query as a string
        :rtype: :class:`rdflib.ConjunctiveGraph`
        """
        risearch_url = 'risearch?'
        http_args = {
            'type': 'triples',
            'lang': 'spo',
            'format': 'N-Triples',
            'query': spo_query,
        }

        rel_url = risearch_url + urlencode(http_args)
        data, abs_url = self.read(rel_url)
        return parse_rdf(data, abs_url, format='n3')

    def spo_search(self, subject=None, predicate=None, object=None):
        """
        Create and run a subject-predicate-object (SPO) search.  Any search terms
        that are not specified will be replaced as a wildcard in the query.

        :param subject: optional subject to search
        :param predicate: optional predicate to search
        :param object: optional object to search
        :rtype: :class:`rdflib.ConjunctiveGraph`
        """
        spo_query = '%s %s %s' % \
                (self.spoencode(subject), self.spoencode(predicate), self.spoencode(object))
        return self.find_statements(spo_query)

    def spoencode(self, val):
        """
        Encode search terms for an SPO query.

        :param val: string to be encoded
        :rtype: string
        """
        if val is None:
            return '*'
        elif "'" in val:    # FIXME: need better handling for literal strings
            return val
        else:
            return '<%s>' % (val,)

    def get_subjects(self, predicate, object):
        """
        Search for all subjects related to the specified predicate and object.

        :param predicate:
        :param object:
        :rtype: generator of RDF statements
        """
        for statement in self.spo_search(predicate=predicate, object=object):
            yield str(statement[0])

    def get_predicates(self, subject, object):
        """
        Search for all subjects related to the specified subject and object.

        :param subject:
        :param object:
        :rtype: generator of RDF statements
        """
        for statement in self.spo_search(subject=subject, object=object):
            yield str(statement[1])

    def get_objects(self, subject, predicate):
        """
        Search for all subjects related to the specified subject and predicate.

        :param subject:
        :param object:
        :rtype: generator of RDF statements
        """
        for statement in self.spo_search(subject=subject, predicate=predicate):
            yield str(statement[2])
