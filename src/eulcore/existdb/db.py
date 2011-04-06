# file existdb/db.py
#
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""Connect to an eXist XML database and query it.

This module provides :class:`ExistDB` and related classes for connecting to
an eXist-db_ database and executing XQuery_ queries against it.

.. _XQuery: http://www.w3.org/TR/xquery/
.. _eXist-db: http://exist.sourceforge.net/

"""

from functools import wraps
import logging
from socket import error as socket_error
from urllib import unquote_plus
import xmlrpclib

from eulcore import xmlmap

__all__ = ['ExistDB', 'QueryResult', 'ExistDBException', 'EXISTDB_NAMESPACE']

logger = logging.getLogger(__name__)

EXISTDB_NAMESPACE = 'http://exist.sourceforge.net/NS/exist'

def _wrap_xmlrpc_fault(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (socket_error, xmlrpclib.Fault, \
            xmlrpclib.ProtocolError, xmlrpclib.ResponseError), e:
                raise ExistDBException(e)
        # FIXME: could we catch IOerror (connection reset) and try again ?
        # occasionally getting this error (so far exclusively in unit tests)
        # error: [Errno 104] Connection reset by peer
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
                uri="%s/xmlrpc" % server_url.rstrip('/'),
                encoding=encoding,
                verbose=verbose,
                allow_none=True,
                use_datetime=True,
            )

    def getDocument(self, name, **kwargs):
        """Retrieve a document from the database.

        :param name: database document path to retrieve
        :rtype: string contents of the document

        """
        logger.debug('getDocumentAsString %s options=%s' % (name, kwargs))
        return self.server.getDocumentAsString(name, kwargs)

    def getDoc(self, name, **kwargs):
        "Alias for :meth:`getDocument`."
        return self.getDocument(name, **kwargs)


    def createCollection(self, collection_name, overwrite=False):
        """Create a new collection in the database.

        :param collection_name: string name of collection
        :param overwrite: overwrite existing document?
        :rtype: boolean indicating success

        """
        if not overwrite and self.hasCollection(collection_name):
            raise ExistDBException(collection_name + " exists")

        logger.debug('createCollection %s' % collection_name)
        return self.server.createCollection(collection_name)

    @_wrap_xmlrpc_fault
    def removeCollection(self, collection_name):
        """Remove the named collection from the database.

        :param collection_name: string name of collection
        :rtype: boolean indicating success

        """
        if (not self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " does not exist")

        logger.debug('removeCollection %s' % collection_name)
        return self.server.removeCollection(collection_name)

    def hasCollection(self, collection_name):
        """Check if a collection exists.

        :param collection_name: string name of collection
        :rtype: boolean

        """
        try:
            logger.debug('describeCollection %s' % collection_name)
            self.server.describeCollection(collection_name)
            return True
        except xmlrpclib.Fault, e:
            s = "collection " + collection_name + " not found"
            if (e.faultCode == 0 and s in e.faultString):
                return False
            else:
                raise ExistDBException(e)

    def reindexCollection(self, collection_name):
        """Reindex a collection.
        Reindex will fail if the eXist user does not have the correct permissions
        within eXist (must be a member of the DBA group).

        :param collection_name: string name of collection
        :rtype: boolean success

        """
        if (not self.hasCollection(collection_name)):
            raise ExistDBException(collection_name + " does not exist")

        # xquery reindex function requires that collection name begin with /db/
        if collection_name[0:3] != '/db':
            collection_name = '/db/' + collection_name.strip('/')

        result = self.query("xmldb:reindex('%s')" % collection_name)
        return result.values[0] == 'true'

    @_wrap_xmlrpc_fault
    def hasDocument(self, document_path):
        """Check if a document is present in eXist.

        :param document_path: string full path to document in eXist
        :rtype: boolean

        """
        if self.describeDocument(document_path) == {}:
            return False
        else:
            return True

    @_wrap_xmlrpc_fault
    def describeDocument(self, document_path):
        """Return information about a document in eXist.
        Includes name, owner, group, created date, permissions, mime-type,
        type, content-length.
        Returns an empty dictionary if document is not found.

        :param document_path: string full path to document in eXist
        :rtype: dictionary

        """
        logger.debug('describeResource %s' % document_path)
        return self.server.describeResource(document_path)

    @_wrap_xmlrpc_fault
    def getCollectionDescription(self, collection_name):
        """Retrieve information about a collection.

        :param collection_name: string name of collection
        :rtype: boolean

        """
        logger.debug('getCollectionDesc %s' % collection_name)
        return self.server.getCollectionDesc(collection_name)

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

        logger.debug('parse %s overwrite=%s' % (path, overwrite))
        return self.server.parse(xml, path, int(overwrite))

    @_wrap_xmlrpc_fault
    def removeDocument(self, name):
        """Remove a document from the database.

        :param name: full eXist path to the database document to be removed
        :rtype: boolean indicating success

        """
        logger.debug('remove %s' % name)
        return self.server.remove(name)

    @_wrap_xmlrpc_fault
    def moveDocument(self, from_collection, to_collection, document):
        """Move a document in eXist from one collection to another.

        :param from_collection: collection where the document currently exists
        :param to_collection: collection where the document should be moved
        :param document: name of the document in eXist
        :rtype: boolean
        """
        self.query("xmldb:move('%s', '%s', '%s')" % \
                            (from_collection, to_collection, document))
        # query result does not return any meaningful content,
        # but any failure (missing collection, document, etc) should result in
        # an exception, so return true if the query completed successfully
        return True

    @_wrap_xmlrpc_fault
    def query(self, xquery, start=1, how_many=10, **kwargs):
        """Execute an XQuery query, returning the results directly.

        :param xquery: a string XQuery query
        :param start: first index to return (1-based)
        :param how_many: maximum number of items to return
        :rtype: the resultType specified at the creation of this ExistDB;
                defaults to :class:`QueryResult`.

        """
        logger.debug('query how_many=%d start=%d args=%s\n%s' % (how_many, start, kwargs, xquery))
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
        logger.debug('executeQuery\n%s' % xquery)
        result_id = self.server.executeQuery(xquery, {})
        logger.debug('result id is %s' % result_id)
        return result_id

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
        summary = self.server.querySummary(result_id)
        logger.debug('querySummary result id %d : ' % result_id + \
                     '%(hits)s hits, query took %(queryTime)s ms' % summary)
        return summary

    @_wrap_xmlrpc_fault
    def getHits(self, result_id):
        """Get the number of hits in a query result.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :rtype: integer representing the number of hits

        """

        hits = self.server.getHits(result_id)
        logger.debug('getHits result id %d : %s' % (result_id, hits))
        return hits

    @_wrap_xmlrpc_fault
    def retrieve(self, result_id, position, highlight=False, **options):
        """Retrieve a single result fragment.

        :param result_id: an integer handle returned by :meth:`executeQuery`
        :param position: the result index to return
        :param highlight: enable search term highlighting in result; optional,
            defaults to False
        :rtype: the query result item as a string

        """        
        if highlight:
            # eXist highlight modes: attributes, elements, or both
            # using elements because it seems most reasonable default
            options['highlight-matches'] = 'elements'
            # pretty-printing with eXist matches can introduce unwanted whitespace
            if 'indent' not in options:
                options['indent'] = 'no'
        logger.debug('retrieve result id %d position=%d options=%s' % (result_id, position, options))
        return self.server.retrieve(result_id, position, options)

    @_wrap_xmlrpc_fault
    def releaseQueryResult(self, result_id):
        """Release a result set handle in the server.

        :param result_id: an integer handle returned by :meth:`executeQuery`

        """
        logger.debug('releaseQueryResult result id %d' % result_id)
        self.server.releaseQueryResult(result_id)

    @_wrap_xmlrpc_fault
    def setPermissions(self, resource, permissions):
        """Set permissions on a resource in eXist.

        :param resource: full path to a collection or document in eXist
        :param permissions: int or string permissions statement
        """
        # TODO: support setting owner, group ?
        logger.debug('setPermissions %s %s' % (resource, permissions))
        self.server.setPermissions(resource, permissions)

    @_wrap_xmlrpc_fault
    def getPermissions(self, resource):
        """Retrieve permissions for a resource in eXist.

        :param resource: full path to a collection or document in eXist
        :rtype: ExistPermissions
        """
        return ExistPermissions(self.server.getPermissions(resource))


    def loadCollectionIndex(self, collection_name, index, overwrite=True):
        """Load an index configuration for the specified collection.
        Creates the eXist system config collection if it is not already there,
        and loads the specified index config file, as per eXist collection and
        index naming conventions.

        :param collection_name: name of the collection to be indexed
        :param index: string or file object with the document contents (as used by :meth:`load`)
        :param overwrite: set to False to disallow overwriting current index (overwrite allowed by default)        
        :rtype: boolean indicating success
        
        """
        index_collection = self._configCollectionName(collection_name)
        # FIXME: what error handling should be done at this level?
        
        # create config collection if it does not exist
        if not self.hasCollection(index_collection):
            self.createCollection(index_collection)

        # load index content as the collection index configuration file
        return self.load(index, self._collectionIndexPath(collection_name), overwrite)

    def removeCollectionIndex(self, collection_name):
        """Remove index configuration for the specified collection.
        If index collection has no documents or subcollections after the index
        file is removed, the configuration collection will also be removed.
        
        :param collection: name of the collection with an index to be removed
        :rtype: boolean indicating success

        """
        # collection indexes information must be stored under system/config/db/collection_name
        index_collection = self._configCollectionName(collection_name)
        
        # remove collection.xconf in the configuration collection
        self.removeDocument(self._collectionIndexPath(collection_name))
        
        desc = self.getCollectionDescription(index_collection)
        # no documents and no sub-collections - safe to remove index collection
        if desc['collections'] == [] and desc['documents'] == []:
            self.removeCollection(index_collection)
            
        return True

    def hasCollectionIndex(self, collection_name):
        """Check if the specified collection has an index configuration in eXist.

        Note: according to eXist documentation, index config file does not *have*
        to be named *collection.xconf* for reasons of backward compatibility.
        This function assumes that the recommended naming conventions are followed.
        
        :param collection: name of the collection with an index to be removed
        :rtype: boolean indicating collection index is present
        
        """
        return self.hasCollection(self._configCollectionName(collection_name)) \
            and self.hasDocument(self._collectionIndexPath(collection_name))


    def _configCollectionName(self, collection_name):
        """Generate eXist db path to the configuration collection for a specified collection
        according to eXist collection naming conventions.
        """
        # collection indexes information must be stored under system/config/db/collection_name
        return "/db/system/config/db/" + collection_name.strip('/')

    def _collectionIndexPath(self, collection_name):
        """Generate full eXist db path to the index configuration file for a specified
        collection according to eXist collection naming conventions.
        """
        # collection indexes information must be stored under system/config/db/collection_name
        return self._configCollectionName(collection_name) + "/collection.xconf"

class ExistPermissions:
    "Permissions for an eXist resource - owner, group, and active permissions."
    def __init__(self, data):
        self.owner = data['owner']
        self.group = data['group']
        self.permissions = data['permissions']

    def __str__(self):
        return "owner: %s; group: %s; permissions: %s" % (self.owner, self.group, self.permissions)

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, str(self))


class QueryResult(xmlmap.XmlObject):
    """The results of an eXist XQuery query"""
    
    start = xmlmap.IntegerField("@start")
    """The index of the first result returned"""

    values = xmlmap.StringListField("exist:value")
    "Generic value (*exist:value*) returned from an exist xquery"

    _raw_count = xmlmap.IntegerField("@count")
    @property
    def count(self):
        """The number of results returned in this chunk"""
        return self._raw_count or 0
    
    _raw_hits = xmlmap.IntegerField("@hits")
    @property
    def hits(self):
        """The total number of hits found by the search"""
        return self._raw_hits or 0

    @property
    def results(self):
        """The result documents themselves as nodes, starting at
        :attr:`start` and containing :attr:`count` members"""
        return self.node.xpath('*')

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

    rpc_prefix = 'RpcConnection: '

    def message(self):        
        "Rough conversion of xmlrpc fault string into something human-readable."
        orig_except = self.args[0]
        if isinstance(orig_except, socket_error):
            # socket error is a tuple of errno, error string
            message = 'I/O Error: %s' % orig_except[1]
        elif isinstance(orig_except, xmlrpclib.ProtocolError):
            message = 'XMLRPC Error at %(url)s: %(code)s %(msg)s' % {
                    'url': orig_except.url,
                    'code': orig_except.errcode,
                    'msg': unquote_plus(orig_except.errmsg)
            }
        # xmlrpclib.ResponseError ?
        elif self.rpc_prefix in str(self):
            # RpcConnection error generally reports eXist-specific errors
            preamble, message = str(self).strip("""'<>\"""").split(self.rpc_prefix)
            # xmldb and xpath calls may have additional error strings:
            message = message.replace('org.exist.xquery.XPathException: ', '')
            message = message.replace('XMLDB exception caught: ', '')
            message = message.replace('[at line 1, column 1]', '')
        else:
            # if all else fails, display the exception as a string
            message = str(original_exception)
        return message

 
# possible sub- exception types:
# document not found (getDoc,remove)
# collection not found 
