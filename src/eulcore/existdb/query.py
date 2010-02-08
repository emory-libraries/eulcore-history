from eulcore.xmlmap.core import load_xmlobject_from_string, getXmlObjectXPath
import re

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
        self._count = None
        self._return_also = []

    @property
    def result_id(self):
        "Return current result id; if not yet set, run current query"
        if self._result_id is None:
            self._runQuery()
        return self._result_id

    def count(self):
        # FIXME: need to test this - how does hits differ from count?
        if self._count is None:
            self._count = self._db.getHits(self.result_id)
        return self._count

    # FIXME: how do you get the count for the non-limited set?

    def _getCopy(self):
        # copy current queryset - for modification via filter/order/etc
        copy = QuerySet(model=self.model, xquery=self.query.getCopy(), using=self._db)        
        copy.partial_return = self.partial_return
        copy._return_also = self._return_also
        return copy

    def filter(self, *args, **kwargs):
        # django-style filters (field__lookuptype)
        #  exact, contains, startswith
        # possibilities to add:
        #   gt/gte,lt/lte, endswith, range, date, isnull (?), regex (?)
        #   search (full-text search with full-text indexing - like contains but faster)

        # create a copy of the current queryset and add filters to the *copy*
        # so the current queryset remains unchanged
        qscopy= self._getCopy()
        
        for arg, value in kwargs.items():
            if '__' in arg:
                parts = arg.split('__')
                if parts and len(parts) > 1:
                    field = parts[0]
                    lookuptype = parts[1]
            else:
                # if arg is just field=foo, check for special terms
                if arg ==  'contains':  #  contains=foo : contains anywhere in node
                    field = '.'         # relative to base query node
                    lookuptype = arg
                else:
                    # otherwise, set lookup type to exact
                    field = arg
                    lookuptype = 'exact'

            # lookup xpath for field; using field as fall-back
            xpath = getXmlObjectXPath(self.model, field) or field
            qscopy.query.add_filter(xpath, lookuptype, value)
        # return copy query string so additional filters can be added or get() called
        return qscopy

    def order_by(self, field):
        # todo: allow multiple fields, ascending/descending
        xpath = field
        if self.model:
            xpath = getXmlObjectXPath(self.model, field) or field

        qscopy = self._getCopy()
        qscopy.query.sort(xpath)
        return qscopy

    def only(self, fields):
        "Limit which fields should be returned; fields should be xpath properties on associated model"
        qscopy = self._getCopy()
        xp_fields = {}
        for f in fields:
            xp_fields[f] = getXmlObjectXPath(self.model, f)
        qscopy.query.return_only(xp_fields)
        qscopy.partial_return = True
        return qscopy

    def also(self, fields):
        "Specify additional fields to be returned; fields should be xpath properties on associated model"        
        qscopy = self._getCopy()
        xp_fields = {}
        for f in fields:
            xp_fields[f] = getXmlObjectXPath(self.model, f)
        qscopy.query.return_also(xp_fields)
        # save field names so they can be mapped in return object
        qscopy._return_also = fields
        return qscopy


    def all(self):
        return self._getCopy()

    # exclude?

    def reset(self):
        """reset any filters and query, reverting to base query created on init"""
        self.query.clear_filters()        
        # if a query has been made to eXist - release result & reset result id
        if self._result_id is not None:
            self.db.releaseQueryResult(self._result_id)
            self._result_id = None
            self._count = None          # clear any count based on this result set
        

    def get(self, *args, **kwargs):
        # store filtered queryset to do count and retrieve on
        fqs = self.filter(*args, **kwargs)
        if fqs.count() == 1:
            return fqs[0]
        else:
            # FIXME/todo: custom exception type?
            raise Exception("get() did not return 1 match - got %s with params %s"
                % (fqs.count(), kwargs))

    def __getitem__(self, k):
        """
        Return a single result or slice of results from the query
        """        
        if not isinstance(k, (slice, int, long)):
           raise TypeError

        if isinstance(k, slice):
            qs = self._getCopy()
            qs.query.set_limits(low=k.start, high=k.stop)            
            return qs

        # check that index is in range
        # for now, not handling any fancy python indexing
        if k < 0 or k > self.count():
            raise IndexError
       
        item = self._db.retrieve(self.result_id, k)
        if self.model is None:
            return item.data
        if self.partial_return:
            return load_xmlobject_from_string(item.data, PartialResultObject)
        else:
            obj =  load_xmlobject_from_string(item.data, self.model)
            for f in self._return_also:
                # map additional return fields in the return object (similar to PartialResultObject)
                setattr(obj, f, obj.dom_node.xpath('string(%s)' % f))
            return obj

    def __iter__(self):
        # rudimentary iterator (django queryset one much more complicated...)
        for i in range(0, self.count()):
            yield self.__getitem__(i)

    def _runQuery(self):
        """
        execute the currently configured xquery
        """
        self._result_id = self._db.executeQuery(self.query.getQuery())

    def getDocument(self, docname):        
        data = self._db.getDoc('/'.join([self.query.collection, docname]))
        # getDoc returns unicode instead of string-- need to decode before handing off to parseString
        return load_xmlobject_from_string(data.encode('utf_8'), self.model)

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
        self.return_fields = {}
        self.additional_return_fields = {}
        self.start = 0
        self.end = None

    def __str__(self):
        return self.getQuery()

    def getCopy(self):
        xq = Xquery(xpath=self.xpath, collection=self.collection)
        for f in self.filters:
            xq.filters.append(f)
        xq.order_by = self.order_by
        xq.return_fields = self.return_fields
        xq.additional_return_fields = self.additional_return_fields
        return xq

    def getQuery(self):
        """
        Generate and return xquery based on configured filters, sorting, return fields.
        Returns xpath or FLOWR XQuery if required based on sorting and return
        """
        xpath = ''
        if self.collection is not None:
            xpath += 'collection("/db/'+ self.collection.lstrip('/') + '")'

        xpath += self.xpath

        for f in self.filters:
            xpath += '[%s]' % (f)

        # requires FLOWR instead of just XQuery  (sort, customized return, etc.)
        if self.order_by or len(self.return_fields) or len(self.additional_return_fields):            
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
            query = '\n'.join([flowr_for, flowr_let, flowr_order, flowr_where, flowr_return])
        else:
            # if FLOWR is not required, just use plain xpath
            query = xpath

        # if either start or end is specified, only retrieve the specified set of results
        # limits need to be done after any sorting or filtering, so subsequencing entire query
        if self.start != 0 or self.end is not None:
            # subsequence takes nodeset, starting position, number of records to return
            # note: xquery starts counting at 1 instead of 0
            if self.end is None:
                end = ''                            # no limit
            else:
                end = self.end - self.start + 1     # number to return
            query = "subsequence(%s, %i, %s)" % (query, self.start + 1, end)

        return query

    def sort(self, field):
        "Add ordering to xquery; sort field assumed relative to base xpath"
        # todo: multiple sort fields; asc/desc?
        self.order_by = field

    def add_filter(self, xpath, type, value):
        """
        Add a filter to the xpath.  Takes xpath, type of filter, and value.
        Filter types currently implemented: contains, startswith, exact
        """
        # possibilities to be added:
        #   gt/gte,lt/lte, endswith, range, date, isnull (?), regex (?)
        #   search (full-text search with full-text indexing - like contains but faster)
        
        if type == 'contains':
            filter = 'contains(%s, "%s")' % (xpath, value)
        if type == 'startswith':
            filter = 'starts-with(%s, "%s")' % (xpath, value)
        if type == 'exact':
            filter = '%s = "%s"' % (xpath, value)
        self.filters.append(filter)


    def return_only(self, fields):
        "Only return the specified fields.  fields should be a dictionary of return name -> xpath"
        for name, xpath in fields.iteritems():
            if name not in self.return_fields:
                self.return_fields[name] = xpath

    def return_also(self, fields):
        """Return additional specified fields.  fields should be a dictionary of return name -> xpath.
           Not compatible with return_only."""
        for name, xpath in fields.iteritems():
            if name not in self.additional_return_fields:
                self.additional_return_fields[name] = xpath


    def _constructReturn(self, xpath_var):
        """Construct the return portion of a FLOWR xquery.
        xpath_var is the xpath variable which return fields should be relative to, e.g. $n
        """
        # return element - use last node of base xpath
        return_el = self.xpath.split('/')[-1]
        if return_el == 'node()':       # FIXME: other () expressions?
            return_el = 'node'

        if len(self.return_fields):
            rblocks = []
            for name, xpath in self.return_fields.iteritems():
                # construct return element with specified field name and xpath
                # return fields are presumed relative to root return variable
                if xpath[0] == '@':
                    rblocks.insert(0, 'attribute %s {%s/%s}' % (name, xpath_var, xpath))
                    # attribute fields must be returned first when constructing FLOWR return
                    # putting attributes at the beginning of the list of return blocks
                else:
                    # define element, e.g. element id {$n/@id/node()}
                    # note: using node() so element *contents* will be in named element instead of nesting elements
                    rblocks.append('element %s {%s/%s/node()}' % (name, xpath_var, xpath))
            r = 'return <%s>\n {' % (return_el)  + ',\n '.join(rblocks) + '\n} </%s>' % (return_el)
        elif len(self.additional_return_fields):
            # return everything under matched node - all attributes, all nodes
            rblocks = ["%s/@*" % xpath_var, "%s/node()" % xpath_var]
            for name, xpath in self.additional_return_fields.iteritems():
                # same logic as return fields above (how to consolidate?)
                if re.search('@[^/]+$', xpath):     # last element in path is an attribute node
                    # set attributes as fields to avoid attribute conflict;
                    rblocks.insert(0, 'element %s {%s/string(%s)}' % (name, xpath_var, xpath))
                else:
                    rblocks.append('element %s {%s/%s/node()}' % (name, xpath_var, xpath))
            r = 'return <%s>\n {' % (return_el)  + ',\n '.join(rblocks) + '\n} </%s>' % (return_el)
        else:
            r = 'return %s' % xpath_var
        return r

    def clear_filters(self):
        self.filters = []

    def set_limits(self, low=None, high=None):
        """
        Adjusts the limits on the results to be retrieved.

        Any limits passed in here are applied relative to the existing
        constraints. So low is added to the current low value and both will be
        clamped to any existing high value.
        """
        # based on set_limits from django.db.models.sql.query
        if high is not None:
            if self.end is not None:
                self.end = min(self.end, self.start + high)
            else:
                self.end = (self.start or 0) + high
        if low is not None:
            if self.end is not None:
                self.start = min(self.end, self.start + low)
            else:
                self.start = (self.start or 0) + low

    def clear_limits(self):
        "Clear any existing limits"
        self.start = 0
        self.end = None



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
        
