"""Connect to an eXist XML database and query it.

This module provides :class:`ExistDB` and related classes for connecting to
an eXist-db_ database and executing XQuery_ queries against it.

.. _XQuery: http://www.w3.org/TR/xquery/
.. _eXist-db: http://exist.sourceforge.net/

"""

from functools import wraps
import xmlrpclib
from eulcore import xmlmap

__all__ = ['ExistDB', 'QueryResult', 'ExistDBException']

def _wrap_xmlrpc_fault(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except xmlrpclib.Fault, e:
            raise ExistDBException(e)
    return wrapper


class ExistDB:

    """Connect to an eXist database, and manipulate and query it.

    Construction doesn't initiate server communication, only store
    information about where the server is, to be used in later
    communications.

    :param server_url: The XML-RPC endpoint of the server, typically
                       ``/xmlrpc`` within the server root.
    :param resultType: The class to use for returning :meth:`query` results;
                       defaults to :class:`QueryResult`
    :param encoding:   The encoding used to communicate with the server;
                       defaults to "UTF-8"
    :param verbose:    When True, print XML-RPC debugging messages to stdout

    """

    def __init__(self, server_url, resultType=None, encoding='UTF-8', verbose=False):
        # FIXME: Will encoding ever be anything but UTF-8? Does this really
        #   need to be part of our public interface?

        self.resultType = resultType or QueryResult

        self.server = xmlrpclib.ServerProxy(
                uri=server_url,
                encoding=encoding,
                verbose=verbose,
                allow_none=True
            )

    def getDoc(self, name, **kwargs):
        """Retrieve a document from the database.

        :param name: database document path to retrieve
        :rtype: string contents of the document

        """
        return self.server.getDocumentAsString(name, kwargs)

    def createCollection(self, collection_name, overwrite=False):
        """Create a new collection in the database.

        :param collection_name: string name of collection
        :param overwrite: overwrite existing document?
        :rtype: boolean indicating success

        """
        if not overwrite and self.hasCollection(collection_name):
            raise ExistDBException(collection_name + " exists")

        return self.server.createCollection(collection_name)

    @_wrap_xmlrpc_fault
    def removeCollection(self, collection_name):
        """Remove the named collection from the database.

        :param collection_name: string name of collection
        :rtype: boolean indicating success

        """
        if (not self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " does not exist")
        return self.server.removeCollection(collection_name)

    def hasCollection(self, collection_name):
        """Check if a collection exists.

        :param collection_name: string name of collection
        :rtype: boolean

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
    def load(self, xml, path, overwrite=False):
        """Insert or overwrite a document in the database.
        
        :param xml: string or file object with the document contents
        :param path: destination location in the database
        :param overwrite: True to allow overwriting an existing document
        :rtype: boolean indicating success

        """
        if hasattr(xml, 'read'):
            xml = xml.read()

        self.server.parse(xml, path, int(overwrite))

    @_wrap_xmlrpc_fault
    def query(self, xquery, start=1, how_many=10, **kwargs):
        """Execute an XQuery_ query, returning the results directly.

        :param xquery: a string XQuery query
        :param start: first index to return (1-based)
        :param how_many: maximum number of items to return
        :rtype: the resultType specified at the creation of this ExistDB;
                defaults to :class:`QueryResult`.

        """
        xml_s = self.server.query(xquery, how_many, start, kwargs)

        # xmlrpclib tries to guess whether the result is a string or
        # unicode, returning whichever it deems most appropriate.
        # Unfortunately, :meth:`~eulcore.xmlmap.load_xmlobject_from_string`
        # requires a byte string. This means that if xmlrpclib gave us a
        # unicode, we need to encode it:
        if isinstance(xml_s, unicode):
            xml_s = xml_s.encode("UTF-8")

        return xmlmap.load_xmlobject_from_string(xml_s, self.resultType)
    
    @_wrap_xmlrpc_fault
    def executeQuery(self, xquery):
        """Execute an XQuery query, returning a server-provided result
        handle.

        :param xquery: a string XQuery query 
        :rtype: an integer handle identifying the query result for future calls

        """
        # NOTE: eXist's xmlrpc interface requires a dictionary parameter.
        #   This parameter is not documented in the eXist docs at
        #   http://demo.exist-db.org/exist/devguide_xmlrpc.xml
        #   so it's not clear what we can pass there.
        return self.server.executeQuery(xquery, {})

    @_wrap_xmlrpc_fault
    def querySummary(self, result_id):
        """Retrieve results summary from a past query.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :rtype: a dict describing the results

        The returned dict has four fields:

         * *queryTime*: processing time in milliseconds

         * *hits*: number of hits in the result set

         * *documents*: a list of lists. Each identifies a document and
           takes the form [`doc_id`, `doc_name`, `hits`], where:

             * *doc_id*: an internal integer identifier for the document
             * *doc_name*: the name of the document as a string
             * *hits*: the number of hits within that document

         * *doctype*: a list of lists. Each contains a doctype public
                      identifier and the number of hits found for this
                      doctype.

        """
        # FIXME: This just exposes the existdb xmlrpc querySummary function.
        #   Frankly, this return is just plain ugly. We should come up with
        #   something more meaningful.
        return self.server.querySummary(result_id)

    @_wrap_xmlrpc_fault
    def getHits(self, result_id):
        """Get the number of hits in a query result.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :rtype: integer representing the number of hits

        """
        return self.server.getHits(result_id)

    @_wrap_xmlrpc_fault
    def retrieve(self, result_id, position, options={}):
        """Retrieve a single result fragment.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :param position: the result index to return
        :rtype: the query result item as a string

        """
        return self.server.retrieve(result_id, position, options)

    @_wrap_xmlrpc_fault
    def releaseQueryResult(self, result_id):
        """Release a result set handle in the server.

        :param result_id: an integer handle returned by :meth:`executeQuery`

        """
        self.server.releaseQueryResult(result_id)


class QueryResult(xmlmap.XmlObject):
    """The results of an eXist XQuery query"""

    start = xmlmap.XPathInteger("@start")
    """The index of the first result returned"""

    _raw_count = xmlmap.XPathInteger("@count")
    @property
    def count(self):
        """The number of results returned in this chunk"""
        return self._raw_count or 0
    
    _raw_hits = xmlmap.XPathInteger("@hits")
    @property
    def hits(self):
        """The total number of hits found by the search"""
        return self._raw_hits or 0

    @property
    def results(self):
        """The result documents themselves as DOM nodes, starting at
        :attr:`start` and containing :attr:`count` members"""
        return self.dom_node.xpath('*')

    # FIXME: Why do we have two properties here with the same value?
    # start == show_from. We should pick one and deprecate the other.
    @property
    def show_from(self):
        """The index of first object in this result chunk.
        
        Equivalent to :attr:`start`."""
        return self.start

    # FIXME: Not sure how we're using this, but it feels wonky. If we're
    # using it for chunking or paging then we should probably follow the
    # slice convention of returning the index past the last one. If we're
    # using it for pretty-printing results ranges then the rVal < 0 branch
    # sounds like an exception condition that should be handled at a higher
    # level. Regardless, shouldn't some system invariant handle the rVal >
    # self.hits branch for us? This whole method just *feels* weird. It
    # warrants some examination.
    @property
    def show_to(self):
        """The index of last object in this result chunk"""
        rVal = (self.start - 1) + self.count
        if rVal > self.hits:
            #show_to can not exceed total hits
            return self.hits
        elif rVal < 0:
            return 0
        else:
            return rVal

    # FIXME: This, too, feels like it checks a number of things that should
    # probably be system invariants. We should coordinate what this does
    # with how it's actually used.
    def hasMore(self):
        """Are there more matches after this one?"""
        if not self.hits or not self.start or not self.count:
            return False
        return self.hits > (self.start + self.count)


class ExistDBException(Exception):
    """A handy wrapper for all errors returned by the eXist server."""

