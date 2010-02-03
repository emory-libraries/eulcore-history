from eulcore.existdb.db import ExistDB
from eulcore.xmlmap.core import load_xmlobject_from_string, getXmlObjectXPath


class QuerySet(object):
    """
    eXist version of django QuerySet - lazy database lookup for a set of objects.
    """
    
    def __init__(self, model=None, xpath=None, using=None, collection=None, xquery=None):
        self.model = model     
        self._db = using

        self.query = Xquery(xpath=xpath, collection=collection)
        if xquery:
            self.query = xquery

        self._result_id = None
        self.partial_return = False

    @property
    def result_id(self):
        "Return current result id; if not yet set, run current query"
        if self._result_id is None:
            self._runQuery()
        return self._result_id

    def count(self):
        # FIXME: need to test this - how does hits differ from count?
        return self._db.getHits(self.result_id)

    def _getCopy(self):
        # copy current queryset - for modification via filter/order/etc
        return QuerySet(model=self.model, xquery=self.query.getCopy(), using=self._db)

    def filter(self, contains=None, *args, **kwargs):

        # create a copy of the current queryset and add filters to the *copy*
        # so the current queryset remains unchanged
        qscopy= self._getCopy()
        # TODO: filter should not modify current queryset, but create a new one and return it
        if contains is not None:
            # proper xquery syntax?  use |= or &= ?
            qscopy.query.add_filter('contains(., "%s")' % contains)

        # very simplistic dynamic field search - for now, using field name as xpath (should get from model)
        for arg, value in kwargs.items():
            parts = arg.split('__')
            if parts and len(parts) > 1:
                xpath = parts[0]
                if self.model:
                    xpath = getXmlObjectXPath(self.model, parts[0]) or parts[0]
                if parts[1] == 'contains':
                    qscopy.query.add_filter('contains(%s, "%s")' % (xpath, value))
                if parts[1] == 'startswith':
                    qscopy.query.add_filter('starts-with(%s, "%s")' % (xpath, value))
            else:
                xpath = arg
                if self.model:
                   xpath = getXmlObjectXPath(self.model, arg)
                qscopy.query.add_filter('%s = "%s"' % (xpath, value))

        # return copy query string so additional filters can be added or get() called
        return qscopy

    def order_by(self, field):
        xpath = field
        if self.model:
            xpath = getXmlObjectXPath(self.model, field) or field

        qscopy = self._getCopy()
        qscopy.query.sort(xpath)
        return qscopy

    def only(self, fields):
        "Limit which fields should be returned"
        qscopy = self._getCopy()
        xp_fields = [getXmlObjectXPath(self.model, f) for f in fields ]
        qscopy.query.return_only(xp_fields)
        qscopy.partial_return = True
        return qscopy



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
        # store filtered queryset to do count and retrieve on
        fqs = self.filter(*args, **kwargs)
        if fqs.count() == 1:
            return fqs[0]
        else:
            # FIXME/todo: custom exception type?
            raise Exception("get() did not return 1 match - got %s with params %s"
                % (fqs.count(), kwargs))

    def __getitem__(self, i):
        """
        Return a single result from the query, by index
        """
        # FIXME: check not negative, in range?
        # todo: support slice?
        item = self._db.retrieve(self.result_id, i)        
        if self.model is None:
            return item.data
        if self.partial_return:
            return load_xmlobject_from_string(item.data, PartialResultObject)
        else:
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
        self.return_fields = []

    def __str__(self):
        return self.getQuery()

    def getCopy(self):
        xq = Xquery(xpath=self.xpath, collection=self.collection)
        for f in self.filters:
            xq.filters.append(f)
        xq.order_by = self.order_by
        return xq

    def getQuery(self):
        xpath = ''
        if self.collection is not None:
            xpath += 'collection("/db/'+ self.collection.lstrip('/') + '")'

        xpath += self.xpath

        for f in self.filters:
            xpath += '[%s]' % (f)

        # requires FLOWR instead of just XQuery
        # (sort, return only, ...?)
        if self.order_by or len(self.return_fields):
            # NOTE: use constructed xpath, with collection (if any)
            flowr_for = 'for $n in ' + xpath
            flowr_let = ''
            # for now, assume sort relative to root element
            if self.order_by:
                flowr_order = 'order by $n/' + self.order_by.lstrip('/')
            else:
                flowr_order = ''
            flowr_where = ''
            flowr_return = self._constructReturn("$n")
            return '\n'.join([flowr_for, flowr_let, flowr_order, flowr_where, flowr_return])

        # if FLOWR is not required, just return the xpath
        return xpath

    def sort(self, field):
        "Add ordering to xquery; sort field assumed relative to base xpath"
        # todo: multiple sort fields; asc/desc?
        self.order_by = field

    def add_filter(self, filter):
        # NOTE: taking as entire string for now, refine later...
        # what form SHOULD filters be accepted in?  queryset syntax?
        self.filters.append(filter)

    def return_only(self, fields):
        "Only return the specified fields."
        for f in fields:
            # attribute fields must be returned first when constructing FLOWR return
            # putting attributes at the beginning of the list of fields
            if '@' in f:
                self.return_fields.insert(0, f)
            else:
                self.return_fields.append(f)

    def _constructReturn(self, xpath_var):
        """Construct the return portion of a FLOWR xquery.
        xpath_var is the xpath variable which return fields should be relative to, ,.g. $n
        """
        # return element - use last node of base xpath
        return_el = self.xpath.split('/')[-1]
        if return_el == 'node()':
            return_el = 'node'

        if len(self.return_fields):
            rblocks = []
            for rf in self.return_fields:
                # return fields are presumed relative to root return variable
                rblocks.append('{%s/%s}' % (xpath_var, rf))      # e.g., {$n/@id}
            r = 'return <%s>\n ' % (return_el)  + '\n '.join(rblocks) + '\n</%s>' % (return_el)
        else:
            r = 'return %s' % xpath_var
        return r

    def clear_filters(self):
        self.filters = []


class PartialResultObject(object):
    """
    Partial result object - for use when only returning specified fields.
    Makes any xml child nodes and attributes accessible as class attributes.
    """
    def __init__(self, dom_node):
        # map all attributes and child nodes as object variables
        for a in dom_node.attributes:
            setattr(self, a[1], dom_node.getAttributeNS(None, a[1]))
        for c in dom_node.childNodes:
            if c.localName:
                setattr(self, c.localName, c.xpath('string()'))
        
