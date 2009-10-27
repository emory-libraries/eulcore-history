import RDF
from base64 import standard_b64encode as b64encode
from soaplib.client import make_service_client
from soaplib.serializers import primitive as soap_types
from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from urllib import urlencode
from urllib2 import urlopen, Request

class Repository(object):
    URI_HAS_MODEL = 'info:fedora/fedora-system:def/model#hasModel'

    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.username = username
        self.password = password

    @property
    def risearch(self):
        return ResourceIndex(self.fedora_root, self.username, self.password)

    def get_objects_with_cmodel(self, cmodel_uri, type=None):
        uris = self.risearch.get_subjects(self.URI_HAS_MODEL, cmodel_uri)
        return [ self.get_object(uri, type) for uri in uris ]

    def get_object(self, pid, type=None):
        if type is None:
            type = DigitalObject
        if pid.startswith('info:fedora/'): # passed a uri
            pid = pid[len('info:fedora/'):]
        return type(pid, self.fedora_root, self.username, self.password)


def read_uri(uri):
    return urlopen(uri).read()

def auth_headers(username, password):
    if username and password:
        token = b64encode('%s:%s' % (username, password))
        return { 'Authorization': 'Basic ' + token }
    else:
        return {}

def make_reader_with_auth(username, password):
    def read_uri_with_auth(uri):
        request = Request(uri, headers=auth_headers(username, password))
        return urlopen(request).read()
    return read_uri_with_auth

def make_rdf_reader_with_auth(username, password):
    def read_rdf_uri_with_auth(uri):
        parser = RDF.Parser('rdfxml')
        request = Request(uri, headers=auth_headers(username, password))
        data = urlopen(request).read()
        return parser.parse_string_as_stream(data, uri)
    return read_rdf_uri_with_auth

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

    def http_auth(self):
        if self.username and self.password:
            return 'Basic ' + b64encode('%s:%s' % (self.username, self.password))

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

    def get_datastreams_as_xml(self):
        return self.rest_api.listDatastreams(self.pid)

    def get_relationships(self):
        read = make_rdf_reader_with_auth(self.username, self.password)
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


class HTTP_API_Base(object):
    def __init__(self, root, username=None, password=None):
        self.fedora_root = root
        self.read_uri = make_reader_with_auth(username, password)

    def read_relative_uri(self, relative_uri, read=None):
        read = read or self.read_uri
        return read(self.fedora_root + relative_uri)
        

class API_A_LITE(HTTP_API_Base):
    def getDatastreamDissemination(self, pid, ds_name, read=None):
        return self.read_relative_uri('get/%s/%s' % (pid, ds_name), read)


class REST_API(HTTP_API_Base):
    def listDatastreams(self, pid):
        return self.read_relative_uri('objects/%s/datastreams.xml' % (pid,))


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

        parser = RDF.NTriplesParser()
        return parser.parse_string_as_stream(data, uri)

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
            yield str(statement.subject.uri)

    def get_predicates(self, subject, object):
        for statement in self.spo_search(subject=subject, object=object):
            yield str(statement.predicate.uri)

    def get_objects(self, subject, predicate):
        for statement in self.spo_search(subject=subject, predicate=predicate):
            yield str(statement.object.uri)
