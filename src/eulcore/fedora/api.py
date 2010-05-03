import httplib
from soaplib.serializers import primitive as soap_types
from soaplib.service import soapmethod
from soaplib.wsgi_soap import SimpleWSGISoapApp
from urllib import urlencode
from urllib2 import urlopen, Request
from urlparse import urljoin, urlsplit
from base64 import standard_b64encode as b64encode
from Ft.Xml.Domlette import NonvalidatingReader

# low-level wrappers for Fedora APIs

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


# fedora apis

class RequestContextManager(object):
    # used by HTTP_API_Base to close http connections automatically and
    # ease connection creation
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
    def describeRepository(self, read=None):
        """
        Get information about a Fedora repository.

        :rtype: string
        """
        http_args = { 'xml': 'true' }
        return self.read_relative_uri('describe?' + urlencode(http_args), read)

    # why not use REST API version of getDatastreamDissemination?
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

    ### API-A methods (access) ####

    # describeRepository not implemented in REST, use API-A-LITE version

    def findObjects(self, query, pid=True,  chunksize=None, session_token=None, read=None):
        """
        Wrapper function for `Fedora REST API findObjects <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-findObjects>`_
        and `Fedora REST API resumeFindObjects <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-resumeFindObjects>`_

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

    # implement getDatastreamDissemination?  (already have  API-A-LITE version...)

    def getDissemination(self, pid, sdefPid, method, method_params={}, read=None):
        # /objects/{pid}/methods/{sdefPid}/{method} ? [method parameters]
        uri = 'objects/%s/methods/%s/%s' % (pid, sdefPid, method)
        if method_params:
            uri += '?' + urlencode(method_params)
        return self.read_relative_uri(uri, read)

    def getObjectHistory(self, pid, read=None):
        # /objects/{pid}/versions ? [format]
        http_args = { 'format' : 'xml'}
        return self.read_relative_uri('objects/%s/versions?%s' % (pid, urlencode(http_args)), read)

    def getObjectProfile(self):
        # /objects/{pid} ? [format] [asOfDateTime]
        pass

    def listDatastreams(self):
        # /objects/{pid}/datastreams ? [format, datetime]
        pass

    def listMethods(self):
        # /objects/{pid}/methods ? [format, datetime]
        # /objects/{pid}/methods/{sdefpid} ? [format, datetime]
        pass

    ### API-M methods (management) ####

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
