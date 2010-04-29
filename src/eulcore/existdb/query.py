"""Provide a prettier, more Pythonic approach to eXist-db access.

This module provides :class:`QuerySet` modeled after `Django QuerySet`_
objects. It's not dependent on Django at all, but it aims to function as a
stand-in replacement in any context that expects one.

.. _Django QuerySet: http://docs.djangoproject.com/en/1.1/ref/models/querysets/

"""

import re
from Ft.Xml.XPath import Compile, Evaluate
from eulcore.xmlmap import load_xmlobject_from_string
from eulcore.xmlmap.fields import StringField, NodeField, IntegerField, NodeListField
from eulcore.xmlmap.core import XmlObjectType

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
        self.partial_fields = {}
        self.additional_fields = {}
        self._count = None

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
        copy.partial_fields = self.partial_fields.copy()
        copy.additional_fields = self.additional_fields.copy()
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
            fields, rest = _split_fielddef(arg, self.model)
            if rest and rest not in qscopy.query.available_filters:
                # there's leftover stuff and it's not a filter we recognize.
                # assume the entire arg is actually one big xpath.
                xpath = arg
                lookuptype = 'exact'
            else:
                # valid filter, or no filter at all
                xpath = _join_field_xpath(fields) or '.'
                lookuptype = rest or 'exact'

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
        xpath = _simple_fielddef_to_xpath(field, self.model) or field
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
        field_objs = {}
        field_xpath = {}

        for f in fields:
            fieldlist, rest = _split_fielddef(f, self.model)
            if fieldlist and not rest:
                field_objs[f] = fieldlist
                field_xpath[f] = _join_field_xpath(fieldlist)
            else:
                field_objs[f] = f
                field_xpath[f] = f

        qscopy = self._getCopy()
        qscopy.partial_fields.update(field_objs)
        qscopy.query.return_only(field_xpath)
        return qscopy

    def also(self, *fields):
        """Return additional data in results.

        :param fields: names of fields in the QuerySet's :attr:`model`

        This method returns an updated copy of the QuerySet: It does not
        modify the original. When results are returned from the updated
        copy, they will contain the specified additional fields.

        """
        field_objs = {}
        field_xpath = {}

        for f in fields:
            fieldlist, rest = _split_fielddef(f, self.model)
            if fieldlist and not rest:
                field_objs[f] = fieldlist
                field_xpath[f] = _join_field_xpath(fieldlist)
            else:
                field_objs[f] = f
                field_xpath[f] = f

        qscopy = self._getCopy()
        qscopy.additional_fields.update(field_objs)
        qscopy.query.return_also(field_xpath)
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

        return_type = self.model
        
        # if there are additional/partial fields that need to override defined fields,
        # define a new class derived from the XmlObject model and map those fields
        if self.partial_fields:
            return_type = _create_return_class(self.model, self.partial_fields)
        elif self.additional_fields:
            return_type = _create_return_class(self.model, self.additional_fields)

        obj = load_xmlobject_from_string(item.data, return_type)
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

    

def _create_return_class(baseclass, override_fields, xpath_prefix=None):
    """
    Define a new return class which extends the specified baseclass and
    overrides the specified fields.

    :param baseclass: the baseclass to be extended; expected to be an instance of XmlObject
    :param override_fields: dictionary of field, list of nodefields - in the format of partial_fields
    	or additional_fields, as genreated by QuerySet.only or QuerySet.also
    :param xpath_prefix: optional, should only be used when recursing.  By default, the xpath
    	for a constructed node is assumed to be the same as the field name; for sub-object fields,
        this parameter is used to pass the prefix in for creating the sub-object class.
    """
    
    classname = "Partial%s" % baseclass.__name__
    class_fields = {}

    # collect names of subobjects, with information needed to create additional return classes 
    subclasses = {}
    subclass_fields = {}
    for name, fields in override_fields.iteritems():
        # nested object fields are indicated by basename__subname
        if '__' in name:
            basename, remainder = name.split('__', 1)
            subclasses[basename] = fields[0]	# list of field types - first type is basename
            if basename not in subclass_fields:
                subclass_fields[basename] = {}
            subclass_fields[basename][remainder] = fields[1:]
            
        else:
            # field with the same type as the original model field, but with xpath of the variable
            # name, to match how additional field results are constructed by Xquery object
            if fields is None or isinstance(fields, basestring):	
		field_type = StringField	# handle special cases like fulltext score
            else:
                field_type = type(fields[-1])
            
            xpath = name
            if xpath_prefix:
                xpath = "__".join((xpath_prefix, name))
            #TODO: create a clone function for nodefield that takes an xpath
            if isinstance(fields[-1], NodeField) or isinstance(fields[-1], NodeListField):
                class_fields[name] = field_type(xpath, fields[-1]._get_node_class())
            else:
                class_fields[name] = field_type(xpath)

    # create subclasses and add to current class fields
    for subclass_name, nodefield in subclasses.iteritems():
        # create a new class derived from the configured nodefield class, with subclass fields
        prefix = subclass_name
        if xpath_prefix:
            prefix = "__".join((xpath_prefix, prefix))
        # new subclass type
        subclass = _create_return_class(nodefield._get_node_class(), subclass_fields[subclass_name],
                                        xpath_prefix=prefix)
        # field type (e.g. NodeField or NodeListField), to be instanced as new subclass
        class_fields[subclass_name] = type(nodefield)(".", subclass) 
    
    # create the new class and set it as the return type to be initialized
    return XmlObjectType(classname, (baseclass,), class_fields)

def _quote_as_string_literal(s):
    return '"' + s.replace('"', '""').replace('&', '&amp;') + '"'

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
            filter = 'contains(%s, %s)' % (xpath, _quote_as_string_literal(value))
        if type == 'startswith':
            filter = 'starts-with(%s, %s)' % (xpath, _quote_as_string_literal(value))
        if type == 'exact':
            filter = '%s = %s' % (xpath, _quote_as_string_literal(value))
        if type == 'fulltext_terms':
            filter = 'ft:query(%s, %s)' % (xpath, _quote_as_string_literal(value))
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

        if self.return_fields:
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
        elif self.additional_return_fields:
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



# some helpers for handling '__'-separated field names:

def _simple_fielddef_to_xpath(fielddef, cls):
    """Convert a foo__bar__baz field definition to the XPath to that node"""
    fields, rest = _split_fielddef(fielddef, cls)
    if fields and not rest:
        return _join_field_xpath(fields)

def _split_fielddef(fielddef, cls):
    """Split a field definition into a list of field objects and any
    leftover bits."""
    field_parts = []

    while fielddef and cls:
        field_name, rest = _extract_fieldpart(fielddef)
        field = cls._fields.get(field_name, None)
        if field is None:
            # the field_name was invalid. leave it in fielddef as remainder
            break

        fielddef = rest
        field_parts.append(field)
        cls = getattr(field, 'node_class', None)

        # if no node_class then keep the field, but everything else is
        # remainder.

    return field_parts, fielddef

def _extract_fieldpart(s):
    """Split a field definition into exactly two __-separated parts. If
    there are no __ in the field definition, leave the second part empty."""
    idx = s.find('__')
    if idx < 0:
        return s, ''
    else:
        return s[:idx], s[idx+2:]

def _join_field_xpath(fields):
    return '/'.join(f.xpath for f in fields)
