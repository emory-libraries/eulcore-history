from functools import wraps
import xmlrpclib
from eulcore import xmlmap

def _wrap_xmlrpc_fault(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except xmlrpclib.Fault, e:
            raise ExistDBException(e)
    return wrapper


class ExistDB:
    #Class to manipualate eXist DB
    #retrival methods generally accept optional arguments
    #   indent:                 return pretty print xml [yes|no]
    #   encoding:               Specifies the character encoding used for the output.
    #                           If the method returns a string, only the XML declaration
    #                           will be modified accordingly.
    #   omit-xml-declaration:   Add XML declaration to the head of the document. [yes | no]
    #   expand-xincludes:       Expand XInclude elements. [yes | no]
    #   process-xsl-pi:         Specifying "yes": XSL processing instructions in the document
    #                           will be processed and the corresponding stylesheet applied to
    #                           the output. [yes | no]
    #   highlight-matches:      Database adds special tags to highlight the strings in the text
    #                           that have triggered a fulltext match. Set to "elements" to
    #                           highlight matches in element values, "attributes" for attribute
    #                           values or "both" for both elements and attributes.
    #   stylesheet:             Use this parameter to specify an XSL stylesheet which should be
    #                           applied to the output. If the parameter contains a relative path,
    #                           the stylesheet will be loaded from the database.
    #   If a stylesheet has been specified with stylesheet, you can also pass it parameters.
    #   Stylesheet parameters are recognized if they start with the prefix stylesheet-param.,
    #   followed by the name of the parameter. The leading "stylesheet-param." string will be
    #   removed before the parameter is passed to the stylesheet.
    #   stylesheet-param.key1 ... stylesheet-param.key2  Stylesheet paramaters

    SERVER_ENCODING     = 'UTF-8'
    SERVER_ALLOW_NONE   = True
    SERVER_VERBOSE      = False

    def __init__(self, server_url, resultType=None, encoding=None, verbose=None):
        # override default settings if passed in
        self.resultType = resultType or QueryResult
        if (encoding):
            self.SERVER_ENCODING = encoding
        if (verbose is not None):
            self.SERVER_VERBOSE = verbose

        self.server = xmlrpclib.ServerProxy(
                uri=server_url,
                encoding=self.SERVER_ENCODING,
                verbose=self.SERVER_VERBOSE,
                allow_none=self.SERVER_ALLOW_NONE
            )

    def getDoc(self, name, **kwargs):
        """
        Retrieve a document from the database.
        name:   path to doc to retrieve ie. "/edc/ICPSR/00002.xml"
        kwargs: (optional) hash or retrieval options see above
        return: String
        """
        return self.server.getDocumentAsString(name, kwargs)

    def createCollection(self, collection_name, over_write=False):
        """
        Creates a new collection in the database.
        collection_name:    string name of collection
        return: boolean
        """
        if (not over_write and self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " exists")

        return self.server.createCollection(collection_name)

    @_wrap_xmlrpc_fault
    def removeCollection(self, collection_name):
        """
        Removes the named collection from the database.
        collection_name:    string name of collection
        return: boolean
        """
        if (not self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " does not exist")
        return self.server.removeCollection(collection_name)

    def hasCollection(self, collection_name):
        """
        Provides information about the collection
        collection_name:    string name of collection
        return: dict['group', 'name', 'created', 'collections', 'owner', 'permissions']
        """
        try:
            self.server.describeCollection(collection_name)
            return True
        except xmlrpclib.Fault, e:
            s = "collection " + collection_name + " not found"
            if (e.faultCode == 0 and s in e.faultString):
                return False
            else:
                raise ExistDBException(e)

    @_wrap_xmlrpc_fault
    def load(self, xml, filename, overwrite=False):
        if not isinstance(xml, str):
            xml = xml.read()

        self.server.parse(xml, filename, int(overwrite))

    @_wrap_xmlrpc_fault
    def query(self, xqry, start=1, how_many=10, **kwargs):
        '''
        Executes an XQuery and returns a xml string
        root of xml string will be
        <exist:result xmlns:exist="http://exist.sourceforge.net/NS/exist" hits="2" start="1" count="2">
        if hits > count more results remain call again with start=count for remaining results
        '''
        xml_s = self.server.query(xqry, how_many, start, kwargs)

        #xmlrpc will sometimes return unicode, force to UTF-8
        if isinstance(xml_s, unicode):
            xml_s = xml_s.encode("UTF-8")

        return xmlmap.load_xmlobject_from_string(xml_s, self.resultType)
    
    @_wrap_xmlrpc_fault
    def executeQuery(self, xqry):
        '''Execute an xquery and return a result id which can be used to retrieve the results
         or summary information about the results'''
        # NOTE: requires hash of parameters, unknown what options are supported
        # should result_id be stored and used for subsequent requests that require a result_id?
        return self.server.executeQuery(xqry, {})

    @_wrap_xmlrpc_fault
    def querySummary(self, result_id):
        '''Summary information about xquery results for a result set by id returned from executeQuery.
           Returns a list of hits, documents (list of document name, integer id, and number of hits),
           and the time it took to run the query.'''
        # should response be converted to some kind of object format?
        return self.server.querySummary(result_id)

    @_wrap_xmlrpc_fault
    def getHits(self, result_id):
        '''Return the number of hits in an xquery result by id returned from executeQuery'''
        return self.server.getHits(result_id)

    @_wrap_xmlrpc_fault
    def retrieve(self, result_id, position, options={}):
        '''Retrieve a single result fragment from result id, by position'''
        return self.server.retrieve(result_id, position, options)

    @_wrap_xmlrpc_fault
    def releaseQueryResult(self, result_id):
        '''Force a result set to be released on the server.
        No return value, no exception when releasing an invalid result id.'''
        self.server.releaseQueryResult(result_id)


class QueryResult(xmlmap.XmlObject):
    start = xmlmap.XPathInteger("@start")

    _raw_count = xmlmap.XPathInteger("@count")
    @property
    def count(self):
        return self._raw_count or 0
    
    _raw_hits = xmlmap.XPathInteger("@hits")
    @property
    def hits(self):
        return self._raw_hits or 0

    @property
    def results(self):
        return self.dom_node.xpath('*')

    @property
    def show_from(self):
        '''
        return position of first object in total results.
        ie:  showing results 51 to 100 of 100:  show_from = 51
        '''
        return self.start

    @property
    def show_to(self):
        '''
        return position of last object in total results.
        ie:  showing results 1 to 50 of 100:  show_to = 50
        '''
        rVal = (self.start - 1) + self.count
        if rVal > self.hits:
            #show_to can not exceed total hits
            return self.hits
        elif rVal < 0:
            return 0
        else:
            return rVal

    def hasMore(self):
        if not self.hits or not self.start or not self.count:
            return False
        return self.hits > (self.start + self.count)


class ExistDBException(Exception):
    pass

