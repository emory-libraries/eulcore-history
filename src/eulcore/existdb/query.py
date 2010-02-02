from eulcore.existdb.db import ExistDB
from eulcore.xmlmap.core import load_xmlobject_from_string, getXmlObjectXPath


class QuerySet(object):
    """
    eXist version of django QuerySet - lazy database lookup for a set of objects.
    """
    
    def __init__(self, model=None, xpath=None, using=None, collection=None):
        self.model = model     
        self._db = using        
        self.query = Xquery(xpath=xpath, collection=collection)

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
            self.query.add_filter('contains(., "%s")' % contains)

        # very simplistic dynamic field search - for now, using field name as xpath (should get from model)
        for arg, value in kwargs.items():
            parts = arg.split('__')
            if parts and len(parts) > 1:
                xpath = parts[0]
                if self.model:
                    xpath = getXmlObjectXPath(self.model, parts[0]) or parts[0]
                if parts[1] == 'contains':
                    self.query.add_filter('contains(%s, "%s")' % (xpath, value))
                if parts[1] == 'startswith':
                    self.query.add_filter('starts-with(%s, "%s")' % (xpath, value))
            else:
                xpath = arg
                if self.model:
                   xpath = getXmlObjectXPath(self.model, arg)
                self.query.add_filter('%s = "%s"' % (xpath, value))

        # return self so additional filters can be added or get() called
        return self

    def order_by(self, field):
        xpath = field
        if self.model:
            xpath = getXmlObjectXPath(self.model, field) or field
            
        return self.query.sort(xpath)

    # exclude?
    # order by      -- probably need an xquery class to handle this (xpath or flowr as needed)
    # only - fields to be returned (need xpath...)

    def reset(self):
        """reset any filters and query, reverting to base query created on init"""
        self.query.clear_filters()
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
        execute whatever query is currently set
        """
        self._result_id = self._db.executeQuery(self.query.getQuery())


class Xquery(object):
    """
    xpath/xquery object
    """

    xpath = '/node()'

    def __init__(self, xpath=None, collection=None):
        if xpath is not None:
            self.xpath = xpath

        self.collection = collection
        self.filters = []
        self.order_by = None

    def __str__(self):
        return self.getQuery()

    def getQuery(self):
        xpath = ''
        if self.collection is not None:
            xpath += 'collection("/db/'+ self.collection.lstrip('/') + '")'

        xpath += self.xpath

        for f in self.filters:
            xpath += '[%s]' % (f)

        # requires FLOWR instead of just XQuery
        # (sort, return only, ...?)
        if self.order_by:
            # NOTE: use constructed xpath, with collection (if any)
            flowr_for = 'for $n in ' + xpath
            flowr_let = ''
            # for now, assume sort relative to root element
            flowr_order = 'order by $n/' + self.order_by.lstrip('/')
            flowr_where = ''
            flowr_return = 'return  $n'
            return '\n'.join([flowr_for, flowr_let, flowr_order, flowr_where, flowr_return])

        # if FLOWR is not required, just return the xpath
        return xpath

    def sort(self, field):
        "Add ordering to xquery; sort field assumed relative to base xpath"
        self.order_by = field

    def add_filter(self, filter):
        # NOTE: taking as entire string for now, refine later...
        # what form SHOULD filters be accepted in?  queryset syntax?
        self.filters.append(filter)

    def clear_filters(self):
        self.filters = []
        
