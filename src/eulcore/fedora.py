import httplib
import rdflib
from StringIO import StringIO
from base64 import standard_b64encode as b64encode
from eulcore import xmlmap
from soaplib.client import make_service_client
from soaplib.serializers import primitive as soap_types
from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from urllib import urlencode
from urllib2 import urlopen, Request
from urlparse import urljoin, urlsplit

# a repository object, basically a handy facade for easy api access

URI_HAS_MODEL = 'info:fedora/fedora-system:def/model#hasModel'

class Repository(object):
    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.username = username
        self.password = password

    @property
    def risearch(self):
        return ResourceIndex(self.fedora_root, self.username, self.password)

    @property
    def rest_api(self):
        return REST_API(self.fedora_root, self.username, self.password)

    def get_objects_with_cmodel(self, cmodel_uri, type=None):
        uris = self.risearch.get_subjects(URI_HAS_MODEL, cmodel_uri)
        return [ self.get_object(uri, type) for uri in uris ]

    def get_object(self, pid, type=None):
        if type is None:
            type = DigitalObject
        if pid.startswith('info:fedora/'): # passed a uri
            pid = pid[len('info:fedora/'):]
        return type(pid, self.fedora_root, self.username, self.password)

    def find_objects(self, type=None, **kwargs):
        type = type or DigitalObject

        # FIXME: query production here is frankly sketchy
        query = ' '.join([ '%s~%s' % (k, v) for k, v in kwargs.iteritems() ])
        read = parse_xml_obj(add_auth(read_uri, self.username, self.password),
                             SearchResults)

        chunk = self.rest_api.findObjects(query, read=read)
        while True:
            for result in chunk.results:
                yield type(result.pid, self.fedora_root, self.username, self.password)

            if chunk.session_token:
                chunk = self.rest_api.findObjects(query, session_token=chunk.session_token, read=read)
            else:
                break

# xml objects to wrap around xml returns from fedora

class ObjectDatastream(xmlmap.XmlObject):
    dsid = xmlmap.XPathString('@dsid')
    label = xmlmap.XPathString('@label')
    mimeType = xmlmap.XPathString('@mimeType')

class ObjectDatastreams(xmlmap.XmlObject):
    pid = xmlmap.XPathString('@pid')
    datastreams = xmlmap.XPathNodeList('datastream', ObjectDatastream)

class SearchResult(xmlmap.XmlObject):
    def __init__(self, dom_node, context=None):
        if context is None:
            context = xmlmap.Context(dom_node, processorNss={'res': 'http://www.fedora.info/definitions/1/0/types/'})
        xmlmap.XmlObject.__init__(self, dom_node, context)

    pid = xmlmap.XPathString('res:pid')

class SearchResults(xmlmap.XmlObject):
    def __init__(self, dom_node, context=None):
        if context is None:
            context = xmlmap.Context(dom_node, processorNss={'res': 'http://www.fedora.info/definitions/1/0/types/'})
        xmlmap.XmlObject.__init__(self, dom_node, context)

    session_token = xmlmap.XPathString('res:listSession/res:token')
    cursor = xmlmap.XPathInteger('res:listSession/res:cursor')
    expiration_date = xmlmap.XPathDate('res:listSession/res:expirationDate')
    results = xmlmap.XPathNodeList('res:resultList/res:objectFields', SearchResult)

# readers used internally to affect how we interpret network data from fedora

def read_uri(uri):
    return urlopen(uri).read()

def auth_headers(username, password):
    if username and password:
        token = b64encode('%s:%s' % (username, password))
        return { 'Authorization': 'Basic ' + token }
    else:
        return {}

def add_auth(reader, username, password):
    def read_uri_with_auth(uri):
        request = Request(uri, headers=auth_headers(username, password))
        return reader(request)
    return read_uri_with_auth

def parse_rdf(reader):
    def read_rdf_uri(uri):
        graph = rdflib.ConjunctiveGraph()
        data = reader(uri)
        # reader returns a string, but graph.parse() wants a file
        graph.parse(StringIO(reader(uri)))
        return graph
    return read_rdf_uri

def parse_xml_obj(reader, xml_class):
    def read_xml_uri(uri):
        data = reader(uri)
        doc = xmlmap.parseString(data, uri)
        return xml_class(doc.documentElement)
    return read_xml_uri

# a single digital object in a repo; basically another facade for api access

class DigitalObject(object):
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
        return 'info:fedora/' + self.pid

    @property
    def api_a_lite(self):
        return API_A_LITE(self.fedora_root, self.username, self.password)

    @property
    def api_m(self):
        return make_service_client(self.fedora_root + 'services/management', API_M())

    @property
    def rest_api(self):
        return REST_API(self.fedora_root, self.username, self.password)

    def get_datastream(self, ds_name, read=None):
        return self.api_a_lite.getDatastreamDissemination(self.pid, ds_name, read)

    def get_datastream_as_xml(self, ds_name, xml_type):
        read = parse_xml_obj(add_auth(read_uri, self.username, self.password),
                             xml_type)
        return self.get_datastream(ds_name, read)

    def get_datastreams(self):
        read = parse_xml_obj(add_auth(read_uri, self.username, self.password),
                             ObjectDatastreams)
        dsobj = self.rest_api.listDatastreams(self.pid, read)
        return dict([ (ds.dsid, ds) for ds in dsobj.datastreams ])

    def get_relationships(self):
        read = parse_rdf(add_auth(read_uri, self.username, self.password))
        return self.get_datastream('RELS-EXT', read)

    def add_relationship(self, rel_uri, object):
        obj_is_literal = True
        if isinstance(object, DigitalObject):
            object = object.pid
            obj_is_literal = False
        elif isinstance(object, str) and object.startswith('info:fedora/'):
            object = object[len('info:fedora/'):]
            obj_is_literal = False

        extra_headers = auth_headers(self.username, self.password)
        return self.api_m.addRelationship(self.pid, rel_uri, object, obj_is_literal, **extra_headers)

    def has_model(self, model):
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

class HTTP_API_Base(object):
    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.username = username
        self.password = password
        self.read_uri = add_auth(read_uri, username, password)

    def read_relative_uri(self, relative_uri, read=None):
        read = read or self.read_uri
        return read(self.fedora_root + relative_uri)
        

class API_A_LITE(HTTP_API_Base):
    def getDatastreamDissemination(self, pid, ds_name, read=None):
        return self.read_relative_uri('get/%s/%s' % (pid, ds_name), read)


class REST_API(HTTP_API_Base):
    def findObjects(self, query, pid=True, session_token=None, read=None):
        http_args = {
            'query': query,
            'resultFormat': 'xml',
        }
        if pid:
            http_args['pid'] = 'true'
        if session_token:
            http_args['sessionToken'] = session_token
        return self.read_relative_uri('objects?' + urlencode(http_args), read)
        
    def listDatastreams(self, pid, read=None):
        return self.read_relative_uri('objects/%s/datastreams.xml' % (pid,), read)


class API_M(SimpleWSGISoapApp):
    # FIXME: also accepts an optional String datatype
    @soapmethod(
            soap_types.String,  # pid
            soap_types.String,  # relationship
            soap_types.String,  # object
            soap_types.Boolean, # isLiteral
            _returns = soap_types.Boolean)
    def addRelationship(self, pid, relationship, object, isLiteral):
        pass


class ResourceIndex(object):
    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.username = username
        self.password = password

    def find_statements(self, spo_query):
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
        spo_query = '%s %s %s' % \
                (self.spoencode(subject), self.spoencode(predicate), self.spoencode(object))
        return self.find_statements(spo_query)

    def spoencode(self, val):
        if val is None:
            return '*'
        else:
            return '<%s>' % (val,)

    def get_subjects(self, predicate, object):
        for statement in self.spo_search(predicate=predicate, object=object):
            yield str(statement[0])

    def get_predicates(self, subject, object):
        for statement in self.spo_search(subject=subject, object=object):
            yield str(statement[1])

    def get_objects(self, subject, predicate):
        for statement in self.spo_search(subject=subject, predicate=predicate):
            yield str(statement[2])
