import xmlrpclib
from django.conf import settings
from Ft.Xml.Domlette import NonvalidatingReader
from django.core.paginator import Paginator, InvalidPage, EmptyPage, Page

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
    SERVER_VERBOSE      = settings.DEBUG

    def __init__(self, resultType=None):
        self.server = xmlrpclib.ServerProxy(uri=settings.EXISTDB_SERVER_URL, encoding=self.SERVER_ENCODING,  verbose=self.SERVER_VERBOSE, allow_none=self.SERVER_ALLOW_NONE)
        if resultType:
            self.resultType = resultType
        else:
            self.resultType = QueryResult

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

    def removeCollection(self, collection_name):
        """
        Removes the named collection from the database.
        collection_name:    string name of collection
        return: boolean
        """
        if (not self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " does not exist")

        try:
            return self.server.removeCollection(collection_name)
        except xmlrpclib.Fault, e:
            raise ExistDBException(e)

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

    def load(self, xml, filename, overwrite=False):
        try:
            if not isinstance(xml, str):
                xml = xml.read()

            self.server.parse(xml, filename, int(overwrite))
        except xmlrpclib.Fault, e:
            raise ExistDBException(e)

    def query(self, xqry, start=1, how_many=10, **kwargs):
        '''
        Executes an XQuery and returns a xml string
        root of xml string will be
        <exist:result xmlns:exist="http://exist.sourceforge.net/NS/exist" hits="2" start="1" count="2">
        if hits > count more results remain call again with start=count for remaining results
        '''
        try:            
            xml_s = self.server.query(xqry, how_many, start, kwargs)
            #xmlrpc will sometimes return unicode, force to UTF-8

            if isinstance(xml_s, unicode):
                xml_s = xml_s.encode("UTF-8")

            return self.resultType(xml_s)
        except xmlrpclib.Fault, e:
            raise ExistDBException(e)

def getNodeText(node):
    """Return the text contained in a dom node (in all child text nodes) or
       the  value of a dom attribute."""
    node.normalize
    # attribute or text element
    if node.nodeValue:
        return node.nodeValue
    # node that contains other elements
    if node.childNodes:
        val = ""
        for c in node.childNodes:
            childval = getNodeText(c)
            if childval:
                val += childval
        return val
    else:
        return None

class XpathString(object):
    """Descriptor for string access via xpath; object must have a dom_node"""
    def __init__(self, xpath):
        self.xpath = xpath

    def __get__(self, obj, objtype):
        node = obj.dom_node.xpath(self.xpath)
        if node:
            val =  getNodeText(node[0]).strip()
            return val
        else:
            return None

    def __set__(self, obj, val):
        node = obj.dom_node.xpath(self.xpath)
        if node:
            node[0].nodeValue = val

class XpathInteger(XpathString):
    """Descriptor for integer access via xpath; object must have a dom_node"""
    # extend XpathString, but cast value to int
    def __get__(self, obj, objtype):
        value = super(XpathInteger, self).__get__(obj, objtype)
        if value:
            return int(value)
        else:
            return 0
            
class XpathStringList(object):
    """Descriptor for accessing a list of strings via xpath; object must have a dom_node"""
    def __init__(self, xpath):
        self.xpath = xpath

    def __get__(self, obj, objtype):        
        nodes = obj.dom_node.xpath(self.xpath)
        result = []
        for n in nodes:
            value = getNodeText(n)
            if value:
                result.append(value.strip())        
        return result

    # not sure how (or if) to do set
    #def __set__(self, obj, val):

class XpathObjectList(object):
    """Descriptor for a list of node-objects via xpath; parent object must
    have a dom_node; object init param is dom_node"""
    # return list of xpath nodes initialized as an arbitrary object type
    def __init__(self, xpath, type):
        self.xpath = xpath
        self.type = type

    def __get__(self, obj, objtype):
        nodes = obj.dom_node.xpath(self.xpath)
        result = []
        for n in nodes:
            result.append(self.type(n))
        return result

class QueryResult:
    hits = XpathInteger("@hits")
    start = XpathInteger("@start")
    count = XpathInteger("@count")
    
    def __init__(self, response_str):
        self.response_str = response_str
        self.dom = NonvalidatingReader.parseString(response_str)
        self.dom_node = self.dom.documentElement

    @property
    def results(self):
        return self.dom.xpath('/*/*')

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
        return self.hits > (self.start + self.count)

class ExistDBException(Exception):
    pass

class ResultPaginator(Paginator):
    def __init__(self, qry_result, result_list, orphans=0, allow_empty_first_page=False):
        self._qry_result = qry_result
        Paginator.__init__(self, result_list, self._qry_result.count, orphans, allow_empty_first_page)

    def _get_count(self):
        "Returns the total number of hits, across all pages."
        self._count = self._qry_result.hits
        return self._count
    count = property(_get_count)

    def page(self, number):
        "Returns a Page object for the given exist result set."
        # Make sure page requested is an int. If not, deliver first page.
        try:
            page = int(number)
        except ValueError:
            page = 1

        #if page request exceeds max pages return last page
        if (page > self.num_pages):
            page = self.num_pages
        elif page < 1:
            page = 1

        #paginator assumes all data was returned however eXist returns data in chunks
        #so we always want all results 
        return Page(self.object_list, page, self)