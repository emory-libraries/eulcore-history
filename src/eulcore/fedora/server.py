import httplib
from StringIO import StringIO
from base64 import standard_b64encode as b64encode
from urllib import urlencode
from urllib2 import urlopen, Request
from urlparse import urljoin, urlsplit

import rdflib
from soaplib.client import make_service_client
from soaplib.serializers import primitive as soap_types
from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from Ft.Xml.Domlette import NonvalidatingReader
from Ft.Xml.XPath.Context import Context

from eulcore import xmlmap

# FIXME: DateField still needs significant improvements before we can make
# it part of the real xmlmap interface.
from eulcore.xmlmap.fields import DateField

# a repository object, basically a handy facade for easy api access

URI_HAS_MODEL = 'info:fedora/fedora-system:def/model#hasModel'

class Repository(object):
    "Pythonic interface to a single Fedora Commons repository instance."
    
    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.username = username
        self.password = password

    @property
    def risearch(self):
        "instance of :class:`ResourceIndex`, with the same root url and credentials"
        return ResourceIndex(self.fedora_root, self.username, self.password)

    @property
    def rest_api(self):
        "instance of :class:`REST_API`, with the same root url and credentials"
        return REST_API(self.fedora_root, self.username, self.password)

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
        return self.rest_api.getNextPID(**kwargs)

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
        return self.rest_api.ingest(**kwargs)

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
        return self.rest_api.purgeObject(**kwargs)

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
        return type(pid, self.fedora_root, self.username, self.password)

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
        read = parse_xml_obj(add_auth(read_uri, self.username, self.password),
                             SearchResults)

        chunk = self.rest_api.findObjects(query, read=read, chunksize=chunksize)
        while True:
            for result in chunk.results:
                yield type(result.pid, self.fedora_root, self.username, self.password)

            if chunk.session_token:
                chunk = self.rest_api.findObjects(query, session_token=chunk.session_token, read=read)
            else:
                break

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

# readers used internally to affect how we interpret network data from fedora

def read_uri(uri):
    "Read the contents of the URI.  Default reader for API calls."
    return urlopen(uri).read()

def auth_headers(username, password):
    "Build HTTP basic authentication headers"
    if username and password:
        token = b64encode('%s:%s' % (username, password))
        return { 'Authorization': 'Basic ' + token }
    else:
        return {}

def add_auth(reader, username, password):
    """
    Add authentication to a reader.
    :param reader: reader function, e.g. :meth:`read_uri`
    :param username:
    :param password:
    """
    def read_uri_with_auth(uri):
        request = Request(uri, headers=auth_headers(username, password))
        return reader(request)
    return read_uri_with_auth

def parse_rdf(reader):
    "Read the contents of a URI and parse it as RDF."
    def read_rdf_uri(uri):
        graph = rdflib.ConjunctiveGraph()
        data = reader(uri)
        # reader returns a string, but graph.parse() wants a file
        graph.parse(StringIO(reader(uri)))
        return graph
    return read_rdf_uri

def parse_xml_obj(reader, xml_class):
    "Read the contents of a URI and convert it to an xml object."
    def read_xml_uri(uri):
        data = reader(uri)
        doc = xmlmap.parseString(data, uri)
        return xml_class(doc.documentElement)
    return read_xml_uri

# a single digital object in a repo; basically another facade for api access

class DigitalObject(object):
    """
    A single digital object in a Fedora respository, with methods for accessing
    the parts of that object.
    """
    def __init__(self, pid, fedora_root, username=None, password=None):
        self.fedora_root = fedora_root
        self.pid = pid
        self.username = username
        self.password = password

    def __str__(self):
        return self.pid

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.pid)

    @property
    def uri(self):
        "Fedora URI for this object (info:fedora form of object pid) "
        return 'info:fedora/' + self.pid

    @property
    def api_a_lite(self):
        "instance of :class:`API_A_LITE`, with the same fedora root url and credentials"
        return API_A_LITE(self.fedora_root, self.username, self.password)

    @property
    def api_m(self):
        "SOAP client for Fedora API-M"
        # FIXME: needs credentials?
        return make_service_client(self.fedora_root + 'services/management', API_M())

    @property
    def rest_api(self):
        "instance of :class:`REST_API`, with the same fedora root url and credentials"
        return REST_API(self.fedora_root, self.username, self.password)

    def get_datastream(self, ds_name, read=None):
        """
        Retrieve one of this object's datastreams from fedora.

        Calls `API-A-LITE getDatastreamDissemination <http://fedora-commons.org/confluence/display/FCR30/API-A-LITE#API-A-LITE-getDatastreamDissemination>`_

        :param ds_name: name of the datastream to be retrieved
        :param read: optional reader function; defaults to :meth:`read_uri`
        :rtype: string
        """
        # TODO: fill out info on read param and return type
        # todo: error handling when attempting to get non-existent datastream
        return self.api_a_lite.getDatastreamDissemination(self.pid, ds_name, read)

    def get_datastream_as_xml(self, ds_name, xml_type):
        """
        Retrieve one of this object's datastreams from fedora and initialize it
        as the specified type of `eulcore.xmlmap.XmlObject`.

        :param ds_name: name of the datastream to be retrieved
        :param xml_type: :class:`~eulcore.xmlmap.XmlObject` type to be returned
        """
        read = parse_xml_obj(add_auth(read_uri, self.username, self.password),
                             xml_type)
        return self.get_datastream(ds_name, read)

    def get_datastreams(self):
        """
        Get all datastreams that belong to this object.

        Returns a dictionary; key is datastream id, value is an :class:`ObjectDatastream`
        for that datastream.

        :rtype: dictionary
        """
        read = parse_xml_obj(add_auth(read_uri, self.username, self.password),
                             ObjectDatastreams)
        dsobj = self.rest_api.listDatastreams(self.pid, read)
        return dict([ (ds.dsid, ds) for ds in dsobj.datastreams ])

    def get_relationships(self):
        """
        Get the relationships for this object from RELS-EXT.

        :rtype: :class:`rdflib.ConjunctiveGraph`
        """
        # FIXME: gets a 404 if object does not have RELS-EXT; throw an exception for this?
        read = parse_rdf(add_auth(read_uri, self.username, self.password))
        return self.get_datastream('RELS-EXT', read)

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
        """
        # TODO: add return type when implemented:
        #:rtype: boolean for success
        obj_is_literal = True
        if isinstance(object, DigitalObject):
            object = object.uri
            obj_is_literal = False
        elif isinstance(object, str) and object.startswith('info:fedora/'):            
            obj_is_literal = False

        extra_headers = auth_headers(self.username, self.password)
        # FIXME: currently no value returned; should be boolean on success
        return self.api_m.addRelationship(self.pid, rel_uri, object, obj_is_literal, **extra_headers)

    def has_model(self, model):
        """
        Check if this object subscribes to the specified content model.

        :param model: URI for the content model, as a string
                    (currently only accepted in info:fedora/foo:### format)
        :rtype: boolean
        """
        # TODO:
        # - return false if object does not have a RELS-EXT datastream
        # - accept DigitalObject for model?
        # - convert model pid to info:fedora/ form if not passed in that way?
        st = (rdflib.URIRef(self.uri), rdflib.URIRef(URI_HAS_MODEL), rdflib.URIRef(model))        
        return st in self.get_relationships()


# make it easy to access a DigitalObject as other types if it has the
# appropriate cmodel info.
class ObjectTypeDescriptor(object):
    def __init__(self, model, objtype):
        self.model = model
        self.objtype = objtype

    def __get__(self, obj, objtype):
        try:
            if obj.has_model(self.model):
                return self.objtype(obj.pid, obj.fedora_root, obj.username, obj.password)
        except:
            return None

# fedora apis

class RequestContextManager(object):
    def __init__(self, method, url, body=None, headers=None):
        self.method = method
        self.url = url
        self.body = body
        self.headers = headers

    def __enter__(self):
        urlparts = urlsplit(self.url)
        if urlparts.scheme == 'http':
            connection = httplib.HTTPConnection(urlparts.hostname, urlparts.port)
        elif urlparts.scheme == 'https':
            connection = httplib.HTTPSConnection(urlparts.hostname, urlparts.port)
        self.connection = connection

        try:
            connection.request(self.method, self.url, self.body, self.headers)
            # FIXME: throw exceptions for HTTP errors
            return connection.getresponse()
        except:
            connection.close()
            raise

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.connection.close()


class HTTP_API_Base(object):
    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.username = username
        self.password = password
        self.read_uri = add_auth(read_uri, username, password)

    def read_relative_uri(self, relative_uri, read=None):
        read = read or self.read_uri
        return read(urljoin(self.fedora_root, relative_uri))

    def relative_request(self, method, rel_path, body=None, headers={}):
        path = urljoin(self.fedora_root, rel_path)
        headers = headers.copy()
        headers.update(auth_headers(self.username, self.password))
        return RequestContextManager(method, path, body, headers)


class API_A_LITE(HTTP_API_Base):
    """
       Python object for accessing `Fedora's API-A-LITE <http://fedora-commons.org/confluence/display/FCR30/API-A-LITE>`_.
    """
    def getDatastreamDissemination(self, pid, ds_name, read=None):
        """
        Retrieve the contents of a single datastream from a fedora object.

        :param pid: object pid
        :param ds_name: datastream id
        :param read: optional reader function; defaults to :meth:`read_uri`
        :rtype: string
        """
        return self.read_relative_uri('get/%s/%s' % (pid, ds_name), read)


class REST_API(HTTP_API_Base):
    """
       Python object for accessing `Fedora's REST API <http://fedora-commons.org/confluence/display/FCR30/REST+API>`_.
    """
    def findObjects(self, query, pid=True,  chunksize=None, session_token=None, read=None):
        """
        Wrapper function for `Fedora REST API findObjects <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-findObjects>`_

        :param query: string of fields and terms to search for
        :param pid: include pid in search results
        :param chunksize: number of objects to return at a time
        :param session_token: get an additional chunk of results from a prior search
        :param read: optional reader function; defaults to :meth:`read_uri`
        :rtype: string
        """
        http_args = {
            'query': query,
            'resultFormat': 'xml',
        }
        if pid:
            http_args['pid'] = 'true'
        if session_token:
            http_args['sessionToken'] = session_token
        if chunksize:
            http_args['maxResults'] = chunksize
        return self.read_relative_uri('objects?' + urlencode(http_args), read)

    def getNextPID(self, numPIDs=None, namespace=None):
        """
        Wrapper function for `Fedora REST API getNextPid <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-getNextPID>`_

        :param numPIDs: (optional) get the specified number of pids; by default, returns 1 
        :param namespace: (optional) get the next pid in the specified pid namespace;
            otherwise, Fedora will return the next pid in the configured default namespace.        
        :rtype: string (if only 1 pid requested) or list of strings (multiple pids)
        """
        http_args = { 'format': 'xml' }
        if numPIDs:
            http_args['numPIDs'] = numPIDs
        if namespace:
            http_args['namespace'] = namespace

        rel_url = 'objects/nextPID?' + urlencode(http_args)
        url = urljoin(self.fedora_root, rel_url)
        with self.relative_request('POST', url, '', {}) as response:
            text = response.read()
        dom = NonvalidatingReader.parseString(text, url)
        pids = [ node.nodeValue for node in dom.xpath('/pidList/pid/text()') ]

        if numPIDs is None:
            return pids[0]
        else:
            return pids

    def ingest(self, text, logMessage=None):
        """
        Ingest a new object into Fedora. Returns the pid of the new object on success.

        Wrapper function for `Fedora REST API ingest <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-ingest>`_

        :param text: full text content of the object to be ingested
        :param logMessage: optional log message
        :rtype: string
        """
        http_args = {}
        if logMessage:
            http_args['logMessage'] = logMessage

        headers = { 'Content-Type': 'text/xml' }

        url = 'objects/new?' + urlencode(http_args)
        with self.relative_request('POST', url, text, headers) as response:
            pid = response.read()

        return pid
            
    def listDatastreams(self, pid, read=None):
        """
        Get a list of all datastreams for a specified object.

        Wrapper function for `Fedora REST API listDatastreams <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-listDatastreams>`_

        :param pid: string object pid
        :param read: optionally specify an alternate reader
        :rtype: string xml data
        """
        return self.read_relative_uri('objects/%s/datastreams.xml' % (pid,), read)

    def purgeObject(self, pid, logMessage=None):
        """
        Purge an object from Fedora.

        Wrapper function for `REST API purgeObject <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-purgeObject>`_

        :param pid: pid of the object to be purged
        :param logMessage: optional log message
        """
        # FIXME: return success/failure?
        http_args = {}
        if logMessage:
            http_args['logMessage'] = logMessage
        
        url = 'objects/' + pid
        with self.relative_request('DELETE', url, '', {}) as response:
            # FIXME: either do something with this response, or else don't
            #   use a context manager here.
            pass

    def getObjectXML(self, pid, read=None):
        """
           Return the entire xml for the specified object.

           :param pid: pid of the object to retrieve
           :param read: optional. alternate reader
           :rtype: string xml content of entire object
        """
        return self.read_relative_uri('objects/%s/objectXML' % (pid,), read)


class API_M(SimpleWSGISoapApp):
    """
       Python object for accessing `Fedora's SOAP API-M <http://fedora-commons.org/confluence/display/FCR30/API-M>`_.
    """
    # FIXME: also accepts an optional String datatype
    @soapmethod(
            soap_types.String,  # pid
            soap_types.String,  # relationship
            soap_types.String,  # object
            soap_types.Boolean, # isLiteral
            _returns = soap_types.Boolean)
    def addRelationship(self, pid, relationship, object, isLiteral):
        """
        Add a new relationship to an object's RELS-EXT datastream.

        Wrapper function for `API-M addRelationship <http://fedora-commons.org/confluence/display/FCR30/API-M#API-M-addRelationship>`_

        :param pid: object pid
        :param relationship: relationship to be added
        :param object: URI or string for related object
        :param isLiteral: boolean, is the related object a literal or an rdf resource
        """
        pass


class ResourceIndex(object):
    "Python object for accessing Fedora's Resource Index."
    
    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.username = username
        self.password = password

    def find_statements(self, spo_query):
        """
        Run an SPO (subject-predicate-object) query and return the results as RDF.

        :param spo_query: SPO query as a string
        :rtype: :class:`rdflib.ConjunctiveGraph`
        """
        risearch_uri = self.fedora_root + '/risearch?'
        http_args = {
            'type': 'triples',
            'lang': 'spo',
            'format': 'N-Triples',
            'query': spo_query,
        }

        uri = risearch_uri + urlencode(http_args)
        request = Request(uri, headers=auth_headers(self.username, self.password))
        data = urlopen(request).read()

        graph = rdflib.ConjunctiveGraph()
        graph.parse(StringIO(data), format='n3')
        return graph

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
