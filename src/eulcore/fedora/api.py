from urllib import urlencode
from urlparse import urlsplit

from soaplib.serializers import primitive as soap_types
from soaplib.serializers.clazz import ClassSerializer
from soaplib.service import soapmethod
from soaplib.client import ServiceClient, SimpleSoapClient
from soaplib.wsgi_soap import SimpleWSGISoapApp

from eulcore.fedora.util import auth_headers, encode_multipart_formdata, \
                                get_content_type

# low-level wrappers for Fedora APIs

class HTTP_API_Base(object):
    def __init__(self, opener):
        self.opener = opener
        self.open = self.opener.open
        self.read = self.opener.read


class REST_API(HTTP_API_Base):
    """
       Python object for accessing `Fedora's REST API <http://fedora-commons.org/confluence/display/FCR30/REST+API>`_.
    """

    # always return xml response instead of html version
    format_xml = { 'format' : 'xml'}

    ### API-A methods (access) #### 
    # describeRepository not implemented in REST, use API-A-LITE version

    def findObjects(self, query, pid=True, chunksize=None, session_token=None):
        """
        Wrapper function for `Fedora REST API findObjects <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-findObjects>`_
        and `Fedora REST API resumeFindObjects <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-resumeFindObjects>`_

        :param query: string of fields and terms to search for
        :param pid: include pid in search results
        :param chunksize: number of objects to return at a time
        :param session_token: get an additional chunk of results from a prior search
        :param parse: optional data parser function; defaults to returning
                      raw string data
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
        return self.read('objects?' + urlencode(http_args))

    def getDatastreamDissemination(self, pid, dsID, asOfDateTime=None):
        # /objects/{pid}/datastreams/{dsID}/content ? [asOfDateTime] [download]
        http_args = {}
        if asOfDateTime:
            http_args['asOfDateTime'] = asOfDateTime
        url = 'objects/%s/datastreams/%s/content?%s' % (pid, dsID, urlencode(http_args))
        return self.read(url)

    def getDissemination(self, pid, sdefPid, method, method_params={}):
        # /objects/{pid}/methods/{sdefPid}/{method} ? [method parameters]
        # not working/implemented?  getting 404
        uri = 'objects/%s/methods/%s/%s/' % (pid, sdefPid, method)
        if method_params:
            uri += '?' + urlencode(method_params)
        return self.read(uri)

    def getObjectHistory(self, pid):
        # /objects/{pid}/versions ? [format]
        return self.read('objects/%s/versions?%s' % (pid, urlencode(self.format_xml)))

    def getObjectProfile(self, pid, asOfDateTime=None): # date?
        # /objects/{pid} ? [format] [asOfDateTime]
        http_args = {}
        if asOfDateTime:
            http_args['asOfDateTime'] = asOfDateTime
        http_args.update(self.format_xml)
        url = 'objects/%s?%s' % (pid, urlencode(http_args))
        return self.read(url)

    def listDatastreams(self, pid):
        """
        Get a list of all datastreams for a specified object.

        Wrapper function for `Fedora REST API listDatastreams <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-listDatastreams>`_

        :param pid: string object pid
        :param parse: optional data parser function; defaults to returning
                      raw string data
        :rtype: string xml data
        """
        # /objects/{pid}/datastreams ? [format, datetime]        
        return self.read('objects/%s/datastreams?%s' % (pid, urlencode(self.format_xml)))

    def listMethods(self, pid, sdefpid=None):
        # /objects/{pid}/methods ? [format, datetime]
        # /objects/{pid}/methods/{sdefpid} ? [format, datetime]
        
        ## NOTE: getting an error when sdefpid is specified; fedora issue?
        
        uri = 'objects/%s/methods' % pid
        if sdefpid:
            uri += '/' + sdefpid
        return self.read(uri + '?' + urlencode(self.format_xml))

    ### API-M methods (management) ####

    def addDatastream(self, pid, dsID, dsLabel,  mimeType, logMessage,
        controlGroup=None, dsLocation=None, altIDs=None, versionable=None,
        dsState=None, formatURI=None, checksumType=None, checksum=None, filename=None):
        # objects/{pid}/datastreams/NEWDS? [opts]
        # content via multipart file in request content, or dsLocation=URI
        # one of dsLocation or filename must be specified

        http_args = { 'dsLabel' : dsLabel, 'mimeType' : mimeType,
            'logMessage' : logMessage}
        if controlGroup:
            http_args['controlGroup'] = controlGroup
        if dsLocation:
            http_args['dsLocation'] = dsLocation
        if altIDs:
            http_args['altIDs'] = altIDs
        if versionable is not None:
            http_args['versionable'] = versionable
        if dsState:
            http_args['dsState'] = dsState
        if formatURI:
            http_args['formatURI'] = formatURI
        if checksumType:
            http_args['checksumType'] = checksumType
        if checksum:
            http_args['checksum'] = checksum

        
        if filename:
            fp = open(filename, 'rb')
            content_type, body = encode_multipart_formdata({}, [ ('file', filename, fp.read())])
            headers = { 'Content-Type' : content_type,
                        'Content-Length' : str(len(body)) }
            fp.close()
        else:
            headers = {}
            body = None

        url = 'objects/%s/datastreams/%s?' % (pid, dsID) + urlencode(http_args)
        with self.open('POST', url, body, headers, throw_errors=False) as response:            
            # expected response: 201 Created (on success)
            # when pid is invalid, response body contains error message
            #  e.g., no path in db registry for [bogus:pid]
            # return success/failure and any additional information
            return (response.status == 201, response.read())

    # addRelationship not implemented in REST API

    def compareDatastreamChecksum(self, pid, dsID, asOfDateTime=None): # date time
        # specical case of getDatastream, with validateChecksum = true
        # currently returns datastream info returned by getDatastream...  what should it return?
        return self.getDatastream(pid, dsID, validateChecksum=True, asOfDateTime=asOfDateTime)

    def export(self, pid, context=None, format=None, encoding=None):
        # /objects/{pid}/export ? [format] [context] [encoding]
        # - if format is not specified, use fedora default (FOXML 1.1)
        # - if encoding is not specified, use fedora default (UTF-8)
        # - context should be one of: public, migrate, archive (default is public)
        http_args = {}
        if context:
            http_args['context'] = context
        if format:
            http_args['format'] = format
        if encoding:
            http_args['encoding'] = encoding
        uri = 'objects/%s/export' % pid
        if http_args:
            uri += '?' + urlencode(http_args)
        return self.read(uri)

    def getDatastream(self, pid, dsID, asOfDateTime=None, validateChecksum=False):
        # /objects/{pid}/datastreams/{dsID} ? [asOfDateTime] [format] [validateChecksum]
        http_args = {}
        if validateChecksum:
            http_args['validateChecksum'] = validateChecksum
        if asOfDateTime:
            http_args['asOfDateTime'] = asOfDateTime
        http_args.update(self.format_xml)        
        uri = 'objects/%s/datastreams/%s' % (pid, dsID) + '?' + urlencode(http_args)
        return self.read(uri)

    # getDatastreamHistory not implemented in REST API

    # getDatastreams not implemented in REST API

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
        return self.read(rel_url, data='')

    def getObjectXML(self, pid):
        """
           Return the entire xml for the specified object.

           :param pid: pid of the object to retrieve
           :param parse: optional data parser function; defaults to returning
                         raw string data
           :rtype: string xml content of entire object
        """
        # /objects/{pid}/objectXML
        return self.read('objects/%s/objectXML' % (pid,))

    # getRelationships not implemented in REST API

    def ingest(self, text, logMessage=None):
        """
        Ingest a new object into Fedora. Returns the pid of the new object on success.

        Wrapper function for `Fedora REST API ingest <http://fedora-commons.org/confluence/display/FCR30/REST+API#RESTAPI-ingest>`_

        :param text: full text content of the object to be ingested
        :param logMessage: optional log message
        :rtype: string
        """

        # FIXME/TODO: add options for ingest with pid, values for label/format/namespace/ownerId, etc?
        http_args = {}
        if logMessage:
            http_args['logMessage'] = logMessage

        headers = { 'Content-Type': 'text/xml' }

        url = 'objects/new?' + urlencode(http_args)
        with self.open('POST', url, text, headers) as response:
            pid = response.read()

        return pid

    def modifyDatastream(self, pid, dsID, dsLabel=None, mimeType=None, logMessage=None, dsLocation=None,
        altIDs=None, versionable=None, dsState=None, formatURI=None, checksumType=None,
        checksum=None, filename=None, content=None, force=False):   
        # /objects/{pid}/datastreams/{dsID} ? [dsLocation] [altIDs] [dsLabel] [versionable] [dsState] [formatURI] [checksumType] [checksum] [mimeType] [logMessage] [force] [ignoreContent]
        # NOTE: not implementing ignoreContent (unneeded)
        
        # content via multipart file in request content, or dsLocation=URI
        # if dsLocation, filename, or content is not specified, datastream content will not be updated

        http_args = {}
        if dsLabel:
            http_args['dsLabel'] = dsLabel
        if mimeType:
            http_args['mimeType'] = mimeType
        if logMessage:
            http_args['logMessage'] = logMessage
        if dsLocation:
            http_args['dsLocation'] = dsLocation
        if altIDs:
            http_args['altIDs'] = altIDs
        if versionable is not None:
            http_args['versionable'] = versionable
        if dsState:
            http_args['dsState'] = dsState
        if formatURI:
            http_args['formatURI'] = formatURI
        if checksumType:
            http_args['checksumType'] = checksumType
        if checksum:
            http_args['checksum'] = checksum
        if force:
            http_args['force'] = force

        headers = {}
        body = None
        if content:
            body = content
            headers = { 'Content-Type' : mimeType,
                        'Content-Length' : str(len(body)) }          
        if filename:
            fp = open(filename, 'rb')
            body = fp.read()
            headers = { 'Content-Type' : get_content_type(filename),
                        'Content-Length' : str(len(body)) }               

        url = 'objects/%s/datastreams/%s?' % (pid, dsID) + urlencode(http_args)
        with self.open('PUT', url, body, headers, throw_errors=False) as response:
            # expected response: 200 (success)
            # response body contains error message, if any
            # return success/failure and any additional information
            return (response.status == 200, response.read())        

    def modifyObject(self, pid, label, ownerId, state, logMessage):
        # /objects/{pid} ? [label] [ownerId] [state] [logMessage]
        http_args = {'label' : label,
                    'ownerId' : ownerId,
                    'state' : state,
                    'logMessage' : logMessage}
        url = 'objects/%s' % (pid,) + '?' + urlencode(http_args)
        with self.open('PUT', url, '', {}, throw_errors=False) as response:
            # returns response code 200 on success
            return response.status == 200

    def purgeDatastream(self, pid, dsID, startDT=None, endDT=None, logMessage=None,
            force=False):
        # /objects/{pid}/datastreams/{dsID} ? [startDT] [endDT] [logMessage] [force]
        http_args = {}
        if logMessage:
            http_args['logMessage'] = logMessage
        if startDT:
            http_args['startDT'] = startDT
        if endDT:
            http_args['endDT'] = endDT
        if force:
            http_args['force'] = force

        url = 'objects/%s/datastreams/%s' % (pid, dsID) + '?' + urlencode(http_args)
        with self.open('DELETE', url, '', {}, throw_errors=False) as response:
            # returns 204 on success (204 No Content)
            # NOTE: response content may be useful on error, e.g.
            #       no path in db registry for [bogus:pid]
            # is there any useful way to pass this info back?
            # *NOTE*: bug when purging non-existent datastream on a valid pid
            # - reported here: http://www.fedora-commons.org/jira/browse/FCREPO-690
            return response.status == 204

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

        url = 'objects/' + pid  + '?' + urlencode(http_args)
        with self.open('DELETE', url, '', {}, throw_errors=False) as response:
            # returns 204 on success (204 No Content)
            return response.status == 204

    # purgeRelationship not implemented in REST API

    def setDatastreamState(self, pid, dsID, dsState):
        # /objects/{pid}/datastreams/{dsID} ? [dsState]
        http_args = { 'dsState' : dsState }
        url = 'objects/%s/datastreams/%s' % (pid, dsID) + '?' + urlencode(http_args)
        with self.open('PUT', url, '', {}, throw_errors=False) as response:
            # returns response code 200 on success
            return response.status == 200

    def setDatastreamVersionable(self, pid, dsID, versionable):
        # /objects/{pid}/datastreams/{dsID} ? [versionable]
        http_args = { 'versionable' : versionable }
        url = 'objects/%s/datastreams/%s' % (pid, dsID) + '?' + urlencode(http_args)
        with self.open('PUT', url, '', {}, throw_errors=False) as response:
            # returns response code 200 on success
            return response.status == 200


# NOTE: the "LITE" APIs are planned to be phased out; when that happens, these functions
# (or their equivalents) should be available in the REST API

class API_A_LITE(HTTP_API_Base):
    """
       Python object for accessing `Fedora's API-A-LITE <http://fedora-commons.org/confluence/display/FCR30/API-A-LITE>`_.
    """
    def describeRepository(self):
        """
        Get information about a Fedora repository.

        :rtype: string
        """
        http_args = { 'xml': 'true' }
        return self.read('describe?' + urlencode(http_args))

    # NOTE: REST API version of getDatastreamDissemination should be preferred
    def getDatastreamDissemination(self, pid, ds_name):
        """
        Retrieve the contents of a single datastream from a fedora object.

        :param pid: object pid
        :param ds_name: datastream id
        :param parse: optional data parser function; defaults to returning
                      raw string data
        :rtype: string
        """
        return self.read('get/%s/%s' % (pid, ds_name))


class API_M_LITE(HTTP_API_Base):
    def upload(self, filename):
        fp = open(filename, 'rb')
        url = 'management/upload'

        content_type, body = encode_multipart_formdata({}, [ ('file', filename, fp.read())])
        headers = { 'Content-Type' : content_type,
                    'Content-Length' : str(len(body)) }

        with self.open('POST', url, body, headers) as response:
            # returns 201 Created on success
            # return response.status == 201
            # content of response should be upload id, if successful
            return response.read()


# return object for getRelationships soap call
class GetRelationshipResponse:
    def __init__(self, relationships):
        self.relationships = relationships

    @staticmethod
    def from_xml(*elements):
        return GetRelationshipResponse([RelationshipTuple.from_xml(el)
                                        for el in elements])

    
class RelationshipTuple(ClassSerializer):
    class types:
        subject = soap_types.String
        predicate = soap_types.String
        object = soap_types.String
        isLiteral = soap_types.Boolean
        datatype = soap_types.String

class GetDatastreamHistoryResponse:
    def __init__(self, datastreams):
        self.datastreams = datastreams

    @staticmethod
    def from_xml(*elements):
        return GetDatastreamHistoryResponse([Datastream.from_xml(el)
                                             for el in elements])

class Datastream(ClassSerializer):
    # soap datastream response used by getDatastreamHistory and getDatastream
    class types:
        controlGroup = soap_types.String
        ID = soap_types.String
        versionID = soap_types.String
        altIDs = soap_types.String   # according to Fedora docs this should be array, but that doesn't work
        label = soap_types.String
        versionable = soap_types.Boolean
        MIMEType = soap_types.String
        formatURI = soap_types.String
        createDate = soap_types.DateTime
        size = soap_types.Integer   # Long ?
        state = soap_types.String
        location = soap_types.String
        checksumType = soap_types.String
        checksum = soap_types.String
    
# service class stub for soap method definitions
class API_M_Service(SimpleWSGISoapApp):
    """
       Python object for accessing `Fedora's SOAP API-M <http://fedora-commons.org/confluence/display/FCR30/API-M>`_.
    """
    # FIXME: also accepts an optional String datatype
    @soapmethod(
            soap_types.String,  # pid       NOTE: fedora docs say URI, but at least in 3.2 it's really pid
            soap_types.String,  # relationship
            soap_types.String,  # object
            soap_types.Boolean, # isLiteral
            _outVariableName='added',
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

    @soapmethod(
            soap_types.String,  # subject (fedora object or datastream URI) 
            soap_types.String,  # relationship
            _outVariableName='relationships',
            _returns = GetRelationshipResponse)   # custom class for complex soap type
    def getRelationships(self, subject=None, relationship=None):
        pass

    @soapmethod(
            soap_types.String,  # pid
            soap_types.String,  # relationship; null matches all
            soap_types.String,  # object; null matches all
            soap_types.Boolean, # isLiteral     # optional literal datatype ?
            _returns = soap_types.Boolean,
            _outVariableName='purged',)
    def purgeRelationship(self, pid, relationship=None, object=None, isLiteral=False):
        pass

    @soapmethod(
            soap_types.String,  #pid
            soap_types.String,  #dsID
            _returns = GetDatastreamHistoryResponse,
            _outVariableName="datastream")
    def getDatastreamHistory(self, pid, dsID):
        pass


# extend SimpleSoapClient to accept auth headers and pass them to any soap call that is made
class AuthSoapClient(SimpleSoapClient):
    def __init__(self, host, path, descriptor, scheme="http", auth_headers={}):
        self.auth_headers = auth_headers
        return super(AuthSoapClient, self).__init__(host, path, descriptor, scheme)

    def __call__(self, *args, **kwargs):
        kwargs.update(self.auth_headers)
        return super(AuthSoapClient, self).__call__(*args, **kwargs)


class API_M(ServiceClient):
    def __init__(self, opener):
        self.auth_headers = auth_headers(opener.username, opener.password)
        urlparts = urlsplit(opener.base_url)
        hostname = urlparts.hostname
        api_path = urlparts.path + 'services/management'
        if urlparts.port:
            hostname += ':%s' % urlparts.port

        # this is basically equivalent to calling make_service_client or ServiceClient init
        # - using custom AuthSoapClient and passing auth headers
        self.server = API_M_Service()
        for method in self.server.methods():
            setattr(self, method.name, AuthSoapClient(hostname, api_path, method,
                urlparts.scheme, self.auth_headers))


class ApiFacade(REST_API, API_A_LITE, API_M_LITE, API_M): # there is no API_A today
    """Pull together all Fedora APIs into one place."""
    def __init__(self, opener):
        HTTP_API_Base.__init__(self, opener)
        API_M.__init__(self, opener)
