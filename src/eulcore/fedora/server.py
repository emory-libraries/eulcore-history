# file fedora/server.py
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

import csv
from urllib import urlencode

from eulcore.fedora.api import HTTP_API_Base, ApiFacade
from eulcore.fedora.models import DigitalObject, URI_HAS_MODEL
# FIXME: should risearch be moved to apis?
from eulcore.fedora.util import RelativeOpener, parse_rdf, parse_xml_object, RequestFailed
from eulcore.fedora.xml import SearchResults, NewPids

# a repository object, basically a handy facade for easy api access

class Repository(object):
    "Pythonic interface to a single Fedora Commons repository instance."

    default_pidspace = None
    """Default namespace to use when requesting new PIDs from Fedora (by default,
    will use Fedora-configured namespace)"""
    default_object_type = DigitalObject
    "Default type to use for methods that return fedora objects - :class:`DigitalObject`"

    search_fields = ['pid', 'label', 'state', 'ownerId', 'cDate', 'mDate',
    'dcmDate', 'title', 'creator', 'subject', 'description', 'publisher',
    'contributor', 'date', 'type', 'format', 'identifier', 'source', 'language',
    'relation', 'coverage', 'rights']
    "fields that can be searched against in :meth:`find_objects`"
    
    search_fields_aliases = {
        'owner' : 'ownerId',
        'created' : 'cDate',
        'modified' : 'mDate',
        'dc_modified' : 'dcmDate'
    }
    "human-readable aliases for oddly-named fedora search fields"
    
    
    def __init__(self, root, username=None, password=None):
        self.opener = RelativeOpener(root, username, password)
        self.api = ApiFacade(self.opener)
        self.fedora_root = root
        self.username = username
        self.password = password
        self._risearch = None

    @property
    def risearch(self):
        "instance of :class:`ResourceIndex`, with the same root url and credentials"
        if self._risearch is None:
            self._risearch = ResourceIndex(self.opener)
        return self._risearch

    def get_next_pid(self, namespace=None, count=None):
        """
        Request next available pid or pids from Fedora, optionally in a specified
        namespace.  Calls :meth:`ApiFacade.getNextPID`.

        :param namespace: (optional) get the next pid in the specified pid namespace;
            otherwise, Fedora will return the next pid in the configured default namespace.
        :param count: (optional) get the specified number of pids; by default, returns 1 pid
        :rtype: string or list of strings
        """
        kwargs = {}
        if namespace is None:
            namespace = self.default_pidspace
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
        success.  Calls :meth:`ApiFacade.ingest`.

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
        Purge an object from Fedora.  Calls :meth:`ApiFacade.purgeObject`.

        :param pid: pid of the object to be purged
        :param log_message: optional log message
        :rtype: boolean
        """        
        kwargs = { 'pid': pid }
        if log_message:
            kwargs['logMessage'] = log_message
        return self.api.purgeObject(**kwargs)

    def get_objects_with_cmodel(self, cmodel_uri, type=None):
        """
        Find objects in Fedora with the specified content model.

        :param cmodel_uri: content model URI (should be full URI in  info:fedora/pid:### format)
        :param type: type of object to return (e.g., class:`DigitalObject`)
        :rtype: list of objects
        """
        uris = self.risearch.get_subjects(URI_HAS_MODEL, cmodel_uri)
        return [ self.get_object(uri, type) for uri in uris ]

    def get_object(self, pid=None, type=None, create=None):
        """
        Initialize a single object from Fedora, or create a new one, with the
        same Fedora configuration and credentials.

        :param pid: pid of the object to request (if not specified,
                    generates a new pid)
        :param type: type of object to return; defaults to :class:`DigitalObject`
        :rtype: single object of the type specified
        :create: boolean: create a new object? (if not specified, defaults
                 to False when pid is specified, and True when it is not)
        """        
        type = type or self.default_object_type

        if pid is None:
            pid = self.get_next_pid()
            if create is None:
                create = True
        else:
            if create is None:
                create = False

        if pid.startswith('info:fedora/'): # passed a uri
            pid = pid[len('info:fedora/'):]

        return type(self.api, pid, create)

    def find_objects(self, terms=None, type=None, chunksize=None, **kwargs):
        """
        Find objects in Fedora.  Find query should be generated via keyword args,
        based on the fields in Fedora documentation.  By default, the query uses
        a contains (~) search for all search terms.  Calls :meth:`ApiFacade.findObjects`.

        Example usage - search for all objects where the owner contains 'jdoe'::
        
            repository.find_objects(ownerId='jdoe')

        Supports all search operators provided by Fedora findObjects query (exact,
        gt, gte, lt, lte, and contains).  To specify the type of query for
        a particular search term, call find_objects like this::

            repository.find_objects(ownerId__exact='lskywalker')
            repository.find_objects(date__gt='20010302')

        :param type: type of objects to return; defaults to :class:`DigitalObject`
        :param chunksize: number of objects to return at a time
        :rtype: generator for list of objects
        """
        type = type or self.default_object_type

        find_opts = {'chunksize' : chunksize}

        search_operators = {
            'exact': '=',
            'gt': '>',
            'gte': '>=',
            'lt': '<',
            'lte': '<=',
            'contains': '~'
        }

        if terms is not None:
            find_opts['terms'] = terms
        else:
            conditions = []
            for field, value in kwargs.iteritems():
                if '__' in field:
                    field, filter = field.split('__')
                    if filter not in search_operators:
                        raise Exception("Unsupported search filter '%s'" % filter)
                    op = search_operators[filter]
                else:
                    op = search_operators['contains']   # default search mode

                if field in self.search_fields_aliases:
                    field = self.search_fields_aliases[field]
                if field not in self.search_fields:
                    raise Exception("Error generating Fedora findObjects query: unknown search field '%s'" \
                                    % field)
                if ' ' in value:
                    # if value contains whitespace, it must be delimited with single quotes
                    value = "'%s'" % value
                conditions.append("%s%s%s" % (field, op, value))
                
            query = ' '.join(conditions)
            find_opts['query'] = query
            
        data, url = self.api.findObjects(**find_opts)
        chunk = parse_xml_object(SearchResults, data, url)
        while True:
            for result in chunk.results:
                yield type(self.api, result.pid)

            if chunk.session_token:
                data, url = self.api.findObjects(session_token=chunk.session_token, **find_opts)
                chunk = parse_xml_object(SearchResults, data, url)
            else:
                break


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

class UnrecognizedQueryLanguage(EnvironmentError):
    pass

class ResourceIndex(HTTP_API_Base):
    "Python object for accessing Fedora's Resource Index."

    RISEARCH_FLUSH_ON_QUERY = False
    """Specify whether or not RI search queries should specify flush=true to obtain
    the most recent results.  If flush is specified to the query method, that
    takes precedence.

    Irrelevant if Fedora RIsearch is configured with syncUpdates = True.
    """

    def find_statements(self, query, language='spo', type='triples', flush=None):
        """
        Run a query in a format supported by the Fedora Resource Index (e.g., SPO
        os Sparql) and return the results.

        :param query: query as a string
        :param language: query language to use; defaults to 'spo'
        :param type: type of query - tuples or triples; defaults to 'triples'
        :param flush: flush results to get recent changes; defaults to False
        :rtype: :class:`rdflib.ConjunctiveGraph` when type is ``triples``; list
            of dictionaries (keys based on return fields) when type is ``tuples``
        """
        risearch_url = 'risearch?'
        http_args = {
            'type': type,
            'lang': language,
            'query': query,
        }
        if type == 'triples':
            format = 'N-Triples'
        elif type == 'tuples':
            format = 'CSV'
        # else - error/exception ?
        http_args['format'] = format

        # if flush parameter was not specified, use class setting
        if flush is None:
            flush = self.RISEARCH_FLUSH_ON_QUERY
        http_args['flush'] = 'true' if flush else 'false'

        rel_url = risearch_url + urlencode(http_args)
        try:
            data, abs_url = self.read(rel_url)
            # parse the result according to requested format
            if format == 'N-Triples':
                return parse_rdf(data, abs_url, format='n3')
            elif format == 'CSV':
                # reader expects a file or a list; for now, just split the string
                # TODO: when we can return url contents as file-like objects, use that
                return csv.DictReader(data.split('\n'))     
        except RequestFailed, f:
            if 'Unrecognized query language' in f.detail:
                raise UnrecognizedQueryLanguage(f.detail)
            # could also see 'Unsupported output format' 
            else:
                raise f
        

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

    def sparql_query(self, query, flush=None):
        """
        Run a Sparql query.

        :param query: sparql query string
        :rtype: list of dictionary
        """
        return self.find_statements(query, language='sparql', type='tuples', flush=flush)
