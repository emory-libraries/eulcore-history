from eulcore.existdb.db import ExistDB
from eulcore.xmlmap.core import load_xmlobject_from_string


class QuerySet(object):
    """
    eXist version of django QuerySet - lazy database lookup for a set of objects.
    """
    
    def __init__(self, model=None, query=None, using=None, collection=None):
        self.model = model
        self._db = using
        # build minimal generic query
        self.query = '/node()'
        if collection is not None:
            self.query = 'collection("/db'+ collection + '")' + self.query
        # copy initial query to base query
        self.base_query = self.query
        self._result_id = None

    @property
    def result_id(self):
        "Return current result id; if not yet set, run current query"
        if self._result_id is None:
            self._runQuery()
        return self._result_id

    def count(self):
        # FIXME: need to test this - how does hits differ from count?
        return self._db.getHits(self.result_id)

    def filter(self, contains=None, *args, **kwargs):        
        if contains is not None:
            # proper xquery syntax?  use |= or &= ?
            self.query += '[contains(., "%s")]' % contains

        # very simplistic dynamic field search - for now, using field name as xpath (should get from model)
        for arg, value in kwargs.items():
            parts = arg.split('__')
            if parts and len(parts) > 1:
                if parts[1] == 'contains':
                    self.query += '[contains(%s, "%s")]' % (parts[0], value)
                if parts[1] == 'startswith':
                    self.query += '[starts-with(%s, "%s")]' % (parts[0], value)
            else:
                self.query += '[%s = "%s"]' % (arg, value)

        # return self so additional filters can be added or get() called
        return self

    # exclude?
    # order by      -- probably need an xquery class to handle this (xpath or flowr as needed)
    # only - fields to be returned (need xpath...)

    def reset(self):
        """reset any filters and query, reverting to base query created on init"""
        self.query = self.base_query
        # if a query has been made to eXist - release result & reset result id
        if self._result_id is not None:
            self.db.releaseQueryResult(self._result_id)
            self._result_id = None
        

    def get(self, *args, **kwargs):
        self.filter(*args, **kwargs)
        if self.count() == 1:
            return self[0]
        else:
            # FIXME/todo: custom exception type?
            raise Exception("get() did not return 1 match - got %s with params %s"
                % (self.count(), kwargs))

    def __getitem__(self, i):
        """
        Return a single result from the query, by index
        """
        # FIXME: check not negative, in range?
        item = self._db.retrieve(self.result_id, i)
        if self.model is None:
            return item.data
        return load_xmlobject_from_string(item.data, self.model)

    def _runQuery(self):
        """
        run whatever query is currently set
        """
        self._result_id = self._db.executeQuery(self.query)