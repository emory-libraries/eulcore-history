"""Provide a prettier, more Pythonic approach to eXist-db access.

This module provides :class:`QuerySet` modeled after `Django QuerySet`_
objects. It's not dependent on Django at all, but it aims to function as a
stand-in replacement in any context that expects one.

.. _Django QuerySet: http://docs.djangoproject.com/en/1.1/ref/models/querysets/

"""

import re
from Ft.Xml.XPath import Compile, Evaluate
from eulcore.xmlmap import XmlObject, load_xmlobject_from_string
from eulcore.xmlmap.core import getXmlObjectXPath

__all__ = ['QuerySet', 'Xquery', 'PartialResultObject']

class QuerySet(object):

    """Lazy eXist database lookup for a set of objects.

    :param model: the type of object to return from :meth:`__getitem__`. If
                  set, the result DOM nodes will be wrapped in objects of
                  this type. Some methods, like :meth:`filter` and
                  :meth:`only` only make sense if this is set. While this
                  argument can be any callable object, it is typically a
                  subclass of :class:`~eulcore.xmlmap.XmlObject`.
    :param xpath: an XPath_ expression where this `QuerySet` will begin
                  filtering. Typically this is left out, beginning with an
                  unfiltered collection: Filtering is then added with
                  :meth:`filter`.
    :param using: The :class:`~eulcore.existdb.db.ExistDB` to query against.
    :param collection: If set, search only within a particular eXist-db
                       collection. Otherwise search all collections.
    :param xquery: Override the entire :class:`Xquery` object used for
                   internal query serialization. Most code will leave this
                   unset, which uses a default :class:`Xquery`.

    .. _XPath: http://www.w3.org/TR/xpath/

    """
    
    def __init__(self, model=None, xpath=None, using=None, collection=None, xquery=None):
        self.model = model     
        self._db = using

        if xquery:
            self.query = xquery
        else:
            self.query = Xquery(xpath=xpath, collection=collection)

        self._result_id = None
        self.partial_return = False
        self._count = None
        self._return_also = []

    @property
    def result_id(self):
        """Return the cached server result id, executing the query first if
        it has not yet executed."""
        if self._result_id is None:
            self._runQuery()
        return self._result_id

    def count(self):
        """Return the cached query hit count, executing the query first if
        it has not yet executed."""
        # FIXME: need to test this - how does hits differ from count?
        if self._count is None:
            self._count = self._db.getHits(self.result_id)
        return self._count

    def queryTime(self):
        """Return the time (in milliseconds) it took for eXist to run the
        query, running the query first if it has not yet executed."""
        # cache summary? is this useful?
        summary = self._db.querySummary(self.result_id)
        return summary['queryTime']

    # FIXME: how do you get the count for the non-limited set?

    def _getCopy(self):
        """Get a clone of the current QuerySet for modification via
        :meth:`filter`, :meth:`order`, etc."""
        # copy current queryset - for modification via filter/order/etc
        copy = QuerySet(model=self.model, xquery=self.query.getCopy(), using=self._db)        
        copy.partial_return = self.partial_return
        copy._return_also = self._return_also
        return copy

    def filter(self, **kwargs):
        """Filter the QuerySet to return a subset of the documents.

        Arguments take the form ``lookuptype`` or ``field__lookuptype``,
        where ``field`` is the name of a field in the QuerySet's :attr:`model`
        and ``lookuptype`` is one of:

         * ``exact`` -- The field or object matches the argument value.
         * ``contains`` -- The field or object contains the argument value.
         * ``startswith`` -- The field or object starts with the argument
           value.
         * ``fulltext_terms`` -- the field or object contains any of the the argument
           terms anywhere in the full text; requires a properly configured lucene index.
           Recommend using fulltext_score for ordering, in return fields.

        Field may be in the format of field__subfield when field is an NodeField
        or NodeListField and subfield is a configured element on that object.

        Any number of these filter arguments may be passed. This method
        returns an updated copy of the QuerySet: It does not modify the
        original.

        """
        # possible future lookup types:
        #   gt/gte,lt/lte, endswith, range, date, isnull (?), regex (?)
        #   search (full-text search with full-text indexing - like contains but faster)

        qscopy = self._getCopy()
        
        for arg, value in kwargs.iteritems():
            if '__' in arg:
                parts = arg.rsplit('__', 1)

            # last section of argument is a known filter
            if '__' in arg and parts[-1] in qscopy.query.available_filters:
                field, lookuptype = parts
            else:
                # if arg is just field=foo, check for special terms
                if arg in ('contains', 'startswith', 'fulltext_terms'):  #  contains=foo : contains anywhere in node
                    field = '.' # relative to base query node
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
        """Order results returned according to a specified field

        :param field: the name (a string) of a field in the QuerySet's
                      :attr:`model`

        This method returns an updated copy of the QuerySet: It does not
        modify the original.

        """

        # TODO: allow multiple fields, ascending/descending
        xpath = field
        if self.model:
            xpath = getXmlObjectXPath(self.model, field) or field

        qscopy = self._getCopy()
        qscopy.query.sort(xpath)
        return qscopy

    def only(self, *fields):
        """Limit results to include only specified fields.

        :param fields: names of fields in the QuerySet's :attr:`model`

        This method returns an updated copy of the QuerySet: It does not
        modify the original. When results are returned from the updated
        copy, they will contain only the specified fields.

        """
        xp_fields = dict((f, getXmlObjectXPath(self.model, f))
                         for f in fields)
        qscopy = self._getCopy()
        qscopy.query.return_only(xp_fields)
        qscopy.partial_return = True
        return qscopy

    def also(self, *fields):
        """Return additional data in results.

        :param fields: names of fields in the QuerySet's :attr:`model`

        This method returns an updated copy of the QuerySet: It does not
        modify the original. When results are returned from the updated
        copy, they will contain the specified additional fields.

        """
        xp_fields = dict((f, getXmlObjectXPath(self.model, f))
                         for f in fields)
        qscopy = self._getCopy()
        qscopy.query.return_also(xp_fields)
        # save field names so they can be mapped in return object
        qscopy._return_also = fields
        return qscopy

    def distinct(self):
        """Return distinct results.
        
        This method returns an updated copy of the QuerySet: It does not
        modify the original. When results are returned from the updated
        copy, they will contain only distinct results.

        """
        qscopy = self._getCopy()
        qscopy.query.distinct()
        return qscopy

    def all(self):
        """Return all results.

        This method returns an identical copy of the QuerySet.
        
        """
        return self._getCopy()

    # exclude?

    def reset(self):
        """Reset filters and cached results on the QuerySet.

        This modifies the current query set, removing all filters, and
        resetting cached results."""
        self.query.clear_filters()        
        # if a query has been made to eXist - release result & reset result id
        if self._result_id is not None:
            self.db.releaseQueryResult(self._result_id)
            self._result_id = None
            self._count = None          # clear any count based on this result set

    def get(self, **kwargs):
        """Get a single result identified by filter arguments.

        Takes any number of :meth:`filter` arguments. Unlike :meth:`filter`,
        though, this method returns exactly one item. If the filter
        expressions match no items, or if they match more than one, this
        method throws an exception.

        """

        fqs = self.filter(**kwargs)
        if fqs.count() == 1:
            return fqs[0]
        else:
            # FIXME/todo: custom exception type?
            # NOTE: django throws a DoesNotExist or a MultipleObjectsReturned
            # see line 338, http://code.djangoproject.com/browser/django/trunk/django/db/models/query.py
            raise Exception("get() did not return 1 match - got %s with params %s"
                % (fqs.count(), kwargs))

    def __getitem__(self, k):
        """Return a single result or slice of results from the query."""        
        if not isinstance(k, (slice, int, long)):
           raise TypeError

        if isinstance(k, slice):
            qs = self._getCopy()
            qs.query.set_limits(low=k.start, high=k.stop)            
            return qs

        # check that index is in range
        # for now, not handling any fancy python indexing
        if k < 0 or k >= self.count():
            raise IndexError
       
        item = self._db.retrieve(self.result_id, k)
        if self.model is None or self.query._distinct:
            return item.data
        if self.partial_return:
            return load_xmlobject_from_string(item.data, PartialResultObject)
        else:
            obj =  load_xmlobject_from_string(item.data, self.model)
            # map additional return fields in the return object (similar to PartialResultObject)
            for f in self._return_also:
                if '__' in f:
                    basename, remainder = f.split('__', 1)
                    # if sub-object does not already exist or is not a partial result subobject, create it
                    # NOTE: will override xpath node mappings
                    if not hasattr(obj, basename) or not isinstance(getattr(obj, basename), PartialResultSubObject):                        
                        setattr(obj, basename, PartialResultSubObject())
                    # get the node for just this field to pass to add_field 
                    nodes = Evaluate(Compile(f), obj.dom_node)
                    getattr(obj, basename).add_field(remainder, nodes[0])
                else:
                    setattr(obj, f, obj.dom_node.xpath('string(%s)' % f))
            # make queryTime method available when retrieving a single item
            setattr(obj, 'queryTime', self.queryTime)
            return obj

    def __iter__(self):
        """Iterate through available results."""
        # rudimentary iterator (django queryset one much more complicated...)
        for i in range(self.count()):
            yield self[i]

    def _runQuery(self):
        """Execute the currently configured query."""
#        print "DEBUG: exist query:\n", self.query.getQuery()
        self._result_id = self._db.executeQuery(self.query.getQuery())

    def getDocument(self, docname):
        """Get a single document from the server by filename."""
        data = self._db.getDocument('/'.join([self.query.collection, docname]))
        # getDocument returns unicode instead of string-- need to decode before handing off to parseString
        return load_xmlobject_from_string(data.encode('utf_8'), self.model)


def _quote_for_string_literal(s):
    return s.replace('"', '""').replace('&', '&amp;')

class Xquery(object):
    """
    xpath/xquery object
    """

    xpath = '/node()'       # default generic xpath
    xq_var = '$n'           # xquery variable to use when constructing flowr query
    available_filters = ['contains', 'startswith', 'exact', 'fulltext_terms']

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
        self._distinct = False

    def __str__(self):
        return self.getQuery()

    def getCopy(self):
        xq = Xquery(xpath=self.xpath, collection=self.collection)
        xq.filters += self.filters
        xq.order_by = self.order_by
        xq._distinct = self._distinct
        # return *copies* of dictionaries, not references to the ones in this object!
        xq.return_fields = self.return_fields.copy()
        xq.additional_return_fields = self.additional_return_fields.copy()
        return xq

    def getQuery(self):
        """
        Generate and return xquery based on configured filters, sorting, return fields.
        Returns xpath or FLOWR XQuery if required based on sorting and return
        """
        xpath_parts = []

        if self.collection is not None:
            xpath_parts.append('collection("/db/' + self.collection.lstrip('/') + '")')

        xpath_parts.append(self.xpath)
        xpath_parts += [ '[%s]' % (f,) for f in self.filters ]

        xpath = ''.join(xpath_parts)
        # requires FLOWR instead of just XQuery  (sort, customized return, etc.)
        if self.order_by or self.return_fields or self.additional_return_fields:
            # NOTE: use constructed xpath, with collection (if any)
            flowr_for = 'for %s in %s' % (self.xq_var, xpath)
            
            flowr_let = ''
            if 'fulltext_score' == self.order_by or 'fulltext_score' in self.return_fields \
                or 'fulltext_score' in self.additional_return_fields:
                flowr_let = 'let $fulltext_score := ft:score(%s)' % self.xq_var
            
            # for now, assume sort relative to root element
            if self.order_by:
                if self.order_by == 'fulltext_score':
                    order_field = '$fulltext_score descending'    # assume highest to lowest when ordering by relevance
                else:
                    order_field = '%s/%s' % (self.xq_var, self.prep_xpath(self.order_by).lstrip('/'))
                flowr_order = 'order by %s' % order_field
            else:
                flowr_order = ''
            flowr_where = ''
            flowr_return = self._constructReturn()
            query = '\n'.join([flowr_for, flowr_let, flowr_order, flowr_where, flowr_return])
        else:
            # if FLOWR is not required, just use plain xpath
            query = xpath

        if self._distinct:
            query = "distinct-values(%s)" % (query,)

        # if either start or end is specified, only retrieve the specified set of results
        # limits need to be done after any sorting or filtering, so subsequencing entire query
        if self.start or self.end is not None:
            # subsequence takes nodeset, starting position, number of records to return
            # note: xquery starts counting at 1 instead of 0
            if self.end is None:
                end = ''                            # no limit
            else:
                end = self.end - self.start         # number to return
            query = "subsequence(%s, %i, %s)" % (query, self.start + 1, end)

        return query

    def sort(self, field):
        "Add ordering to xquery; sort field assumed relative to base xpath"
        # todo: multiple sort fields; asc/desc?
        self.order_by = field

    def distinct(self):
        self._distinct = True

    def add_filter(self, xpath, type, value):
        """
        Add a filter to the xpath.  Takes xpath, type of filter, and value.
        Filter types currently implemented:
         * contains
         * startswith
         * exact
         * fulltext_terms - full-text query; requires lucene index configured in exist

        """
        # possibilities to be added:
        #   gt/gte,lt/lte, endswith, range, date, isnull (?), regex (?)
        #   search (full-text search with full-text indexing - like contains but faster)

        if type not in self.available_filters:
            raise TypeError(repr(type) + ' is not a supported filter type')
        
        if type == 'contains':
            filter = 'contains(%s, "%s")' % (xpath, _quote_for_string_literal(value))
        if type == 'startswith':
            filter = 'starts-with(%s, "%s")' % (xpath, _quote_for_string_literal(value))
        if type == 'exact':
            filter = '%s = "%s"' % (xpath, _quote_for_string_literal(value))
        if type == 'fulltext_terms':
            filter = 'ft:query(%s, "%s")' % (xpath, _quote_for_string_literal(value))
        self.filters.append(filter)


    def return_only(self, fields):
        "Only return the specified fields.  fields should be a dictionary of return name -> xpath"
        self.return_fields.update(fields)

    def return_also(self, fields):
        """Return additional specified fields.  fields should be a dictionary of return name -> xpath.
           Not compatible with return_only."""
        self.additional_return_fields.update(fields)

    def _constructReturn(self):
        """Construct the return portion of a FLOWR xquery."""
        # return element - use last node of base xpath
        return_el = self.xpath.split('/')[-1].strip('@')
        if return_el == 'node()':       # FIXME: other () expressions?
            return_el = 'node'

        if len(self.return_fields):
            rblocks = []
            for name, xpath in self.return_fields.iteritems():
                # construct return element with specified field name and xpath
                # - return fields are presumed relative to root return variable
                # - attributes returned as elements for simplicity, use with distinct, etc.
                if name == 'fulltext_score':
                    rblocks.append('element %s {$fulltext_score}' % name)
                else:
                    if xpath[0] == '@':
                        xpath = "string(%s)" % xpath        # put contents of attribute in constructed element
                    elif '(' not in xpath:          # do not add node() if xpath contains a function (likely to breaks things)
                        # note: using node() so element *contents* will be in named element instead of nesting elements
                        xpath = "%s/node()" % xpath
                    xpath = self.prep_xpath(xpath)
                    
                    # define element, e.g. element id {$n/title/node()} or {$n/string(@id)}
                    rblocks.append('element %s {%s/%s}' % (name, self.xq_var, xpath))
                
            r = 'return <%s>\n {' % (return_el)  + ',\n '.join(rblocks) + '\n} </%s>' % (return_el)
        elif len(self.additional_return_fields):
            # return everything under matched node - all attributes, all nodes
            rblocks = ["%s/@*" % self.xq_var, "%s/node()" % self.xq_var]
            for name, xpath in self.additional_return_fields.iteritems():
                if name == 'fulltext_score':
                    rblocks.append('element %s {$fulltext_score}' % name)
                else:
                    # similar logic as return fields above (how to consolidate?)
                    if re.search('@[^/]+$', xpath):     # last element in path is an attribute node
                        # set attributes as fields to avoid attribute conflict;
                        rblocks.append('element %s {%s/string(%s)}' % (name, self.xq_var, xpath))
                    else:
                        if '(' in xpath:
                            node = ""
                        else:
                            node = "/node()"
                        rblocks.append('element %s {%s/%s%s}' % (name, self.xq_var, xpath, node))
            r = 'return <%s>\n {' % (return_el)  + ',\n '.join(rblocks) + '\n} </%s>' % (return_el)
        else:
            r = 'return %s' % self.xq_var
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

    def prep_xpath(self, xpath):
        # common xpath clean-up before handing off to exist
        # FIXME: this will break on /foo[bar="|./"]
        # FIXME: move return field xpath manip here?  perhaps add param to set type of xpath?

        # mutiple nodes |ed together- fix context issuse by replacing . with xq variable
        if '|./' in xpath:
            xpath  = xpath.replace("|./", "|%s/" % self.xq_var)
        return xpath

class PartialResultObject(object):
    """
    Partial result object - for use when only returning specified fields.
    Makes any xml child nodes and attributes accessible as class attributes.
    Nodes with __ separated names will be mapped as subobjects, e.g. foo__bar
    will be accessible as foo.bar
    """
    def __init__(self, dom_node):
        # map all attributes and child nodes as object variables
        for a in dom_node.attributes:
            setattr(self, a[1], dom_node.getAttributeNS(None, a[1]))
        for c in dom_node.childNodes:
            if c.localName:
                self.add_field(c.localName, c)

    def add_field(self, name, dom_node):
        if '__' in name:
            basename, remainder = name.split('__', 1)
            # if sub-object does not already exist, create it
            if not hasattr(self, basename):
                setattr(self, basename, PartialResultSubObject())

            getattr(self, basename).add_field(remainder, dom_node)
        else:
            setattr(self, name, XmlObject(dom_node))

# extend partial result object - inherits add_field, but no dom_node for constructor
class PartialResultSubObject(PartialResultObject):
    def __init__(self):
        pass
