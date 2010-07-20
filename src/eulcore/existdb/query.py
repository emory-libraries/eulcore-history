"""Provide a prettier, more Pythonic approach to eXist-db access.

This module provides :class:`QuerySet` modeled after `Django QuerySet`_
objects. It's not dependent on Django at all, but it aims to function as a
stand-in replacement in any context that expects one.

.. _Django QuerySet: http://docs.djangoproject.com/en/1.1/ref/models/querysets/

"""

from eulcore.xmlmap import load_xmlobject_from_string
from eulcore.xmlmap.fields import StringField, DateField, NodeField, NodeListField
from eulcore.xmlmap.core import XmlObjectType
from eulcore.xpath import ast, parse, serialize
from eulcore.existdb.exceptions import DoesNotExist, ReturnedMultiple

__all__ = ['QuerySet', 'Xquery']

# TODO: update field info (currently only name/xpath?) passed to Query
# object to include field type (e.g., StringField, NodeField) so that we
# can handle Node and List field types more intelligently.
# Note that any changes in the return structure for NodeFields will
# most likely require a corresponding change in the _create_return_class function


class QuerySet(object):

    """Lazy eXist database lookup for a set of objects.

    :param model: the type of object to return from :meth:`__getitem__`. If
                  set, the resulting xml nodes will be wrapped in objects of
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

        # remove leading / from collection name if present
        collection = collection.lstrip('/') if collection is not None else None
        if xquery:
            self.query = xquery
        else:
            self.query = Xquery(xpath=xpath, collection=collection)

        self._result_id = None
        self.partial_fields = {}
        self.additional_fields = {}
        self._count = None
        self._result_cache = {}
        self._start = 0
        self._stop = None
        self._return_type = None
        self._highlight_matches = False

    def __del__(self):
        # release any queries in eXist 
        if self._result_id is not None:
            self._db.releaseQueryResult(self._result_id)

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
        # if we are in a sliced subset of the query result with a defined end,
        # return the slice length
        if self._stop is not None:
            return self._stop - self._start
        
        if self._count is None:
            self._count = self._db.getHits(self.result_id)
            
        return self._count - self._start

    def queryTime(self):
        """Return the time (in milliseconds) it took for eXist to run the
        query, running the query first if it has not yet executed."""
        # FIXME: should summary be cached ?
        summary = self._db.querySummary(self.result_id)
        return summary['queryTime']

    def _getCopy(self):
        """Get a clone of the current QuerySet for modification via
        :meth:`filter`, :meth:`order`, etc."""
        # copy current queryset - for modification via filter/order/etc
        copy = QuerySet(model=self.model, xquery=self.query.getCopy(), using=self._db)        
        copy.partial_fields = self.partial_fields.copy()
        copy.additional_fields = self.additional_fields.copy()
        copy._highlight_matches = self._highlight_matches
        # reset result cache, if any, because any filters will change it
        copy._result_cache = {}   
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

            # enable highlighting when a full-text query is used
            if lookuptype == 'fulltext_terms':
                qscopy._highlight_matches = True

        # return copy query string so additional filters can be added or get() called
        return qscopy

    def order_by(self, field):
        """Order results returned according to a specified field.  By default,
        all sorting is in ascending order.

        :param field: the name (a string) of a field in the QuerySet's
                      :attr:`model`.  If the field is prefixed with '-', results
                      will be sorted in descending order.

        Example usage for descending sort::
        
            queryset.filter(fulltext_terms='foo').order_by('-fulltext_score')

        This method returns an updated copy of the QuerySet. It does not
        modify the original.
        """
        sort_opts = {}
        if field[0] == '-':
            sort_opts = {'ascending': False }
            field = field[1:]
        # TODO: allow multiple fields
        xpath = _simple_fielddef_to_xpath(field, self.model) or field
        qscopy = self._getCopy()
        qscopy.query.sort(xpath, **sort_opts)
        return qscopy

    def only(self, *fields):
        """Limit results to include only specified fields.        

        :param fields: names of fields in the QuerySet's :attr:`model`

        This method returns an updated copy of the QuerySet: It does not
        modify the original. When results are returned from the updated
        copy, they will contain only the specified fields.

        Special fields available:
         * ``fulltext_score`` - lucene query; should only be used when a fulltext
           query has been used
         * ``document_name``, ``collection_name`` - document or collection name
           where xml content is stored in eXist
         * ``hash`` - generate and return a SHA-1 checksum of the root element being queried
         * ``last_modified`` - :class:`~eulcore.xmlmap.fields.DateField` for the date
           the document the xml element belongs to was last modified

        **NOTE:** Be aware that this will result in an XQuery with a constructed return.
        For large queries, this may have a significant impact on performance.
        For more details, see http://exist.sourceforge.net/tuning.html#N103A2 .
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

        For special fields available, see :meth:`only`.

        For performance considerations, see note on :meth:`only`.
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
            self._db.releaseQueryResult(self._result_id)
            self._result_id = None
            self._count = None          # clear any count based on this result set

    def get(self, **kwargs):
        """Get a single result identified by filter arguments.

        Takes any number of :meth:`filter` arguments. Unlike :meth:`filter`,
        though, this method returns exactly one item. If the filter
        expressions match no items, or if they match more than one, this
        method throws an exception.

        Raises a :class:`eulcore.existdb.exceptions.DoesNotExist` exception if
        no matches are found; raises a :class:`eulcore.existdb.exceptions.ReturnedMultiple`
        exception if more than one match is found.
        """

        fqs = self.filter(**kwargs)
        if fqs.count() == 1:
            return fqs[0]
        # NOTE: behaves like django - throws a DoesNotExist or a MultipleObjectsReturned
        elif fqs.count() == 0:
            raise DoesNotExist("no match found with params %s" % kwargs)
        else:
            raise ReturnedMultiple("returned %s with params %s" % (fqs.count(), kwargs))

    def __getitem__(self, k):
        """Return a single result or slice of results from the query."""
        if not isinstance(k, (slice, int, long)):
           raise TypeError
        
        if isinstance(k, slice):
            qs = self._getCopy()
            # if start was specified, use it; otherwise retain current start
            if k.start is not None:
                qs._start = int(k.start)
            # if a slice bigger than available results is requested, cap it at actual max
            qs._stop = min(k.stop, self.count())

            # because the slicing is done within the result cache,
            # share the same cache across subsets of this queryset
            qs._result_cache = self._result_cache # FIXME: would it be better/safer to use a copy?

            return qs

        # check that index is in range
        # for now, not handling any fancy python indexing
        if k < 0 or k >= self.count():
            raise IndexError

        # calculate the actual index for retrieval from eXist and storage result
        # cache based on the start of the current slice
        i = k + self._start

        if i not in self._result_cache:
            # if the requested item has not yet been retrieved, get it from eXist
            item = self._db.retrieve(self.result_id, i, highlight=self._highlight_matches)
            if self.model is None or self.query._distinct:
                self._result_cache[i] = item.data
            else:
                obj = load_xmlobject_from_string(item.data, self.return_type)
                # make queryTime method available when retrieving a single item
                setattr(obj, 'queryTime', self.queryTime)
                self._result_cache[i] = obj

        return self._result_cache[i]

    @property
    def return_type(self):
        """Return type that will be used for initializing results returned from
        eXist queries.  Either the subclass of :class:`~eulcore.xmlmap.XmlObject`
        passed in to the constructor as model, or, if :meth:`only` or :meth:`also`
        has been used, a dynamically created instance of :class:`~eulcore.xmlmap.XmlObject`
        with the xpaths modified based on the constructed xml return.
        """
        if self._return_type is None:
            self._return_type = self.model

            # if there are additional/partial fields that need to override defined fields,
            # define a new class derived from the XmlObject model and map those fields
            if self.partial_fields:
                self._return_type = _create_return_class(self.model, self.partial_fields,
                        override_xpaths=self.query.get_return_xpaths())
            elif self.additional_fields:
                self._return_type = _create_return_class(self.model, self.additional_fields,
                        override_xpaths=self.query.get_return_xpaths())
        return self._return_type

    def __iter__(self):
        """Iterate through available results."""
        # rudimentary iterator (django queryset one much more complicated...)
        for i in range(self.count()):
            yield self[i]

    def __len__(self):
        # FIXME: is this sufficient?
        # in django, calling len() populates the cache...
        return self.count()

    def _runQuery(self):
        """Execute the currently configured query."""
#        print "DEBUG: exist query:\n", self.query.getQuery()
        self._result_id = self._db.executeQuery(self.query.getQuery())

    def getDocument(self, docname):
        """Get a single document from the server by filename."""
        data = self._db.getDocument('/'.join([self.query.collection, docname]))
        # getDocument returns unicode instead of string-- need to decode before handing off to parseString
        return load_xmlobject_from_string(data.encode('utf_8'), self.model)

    

def _create_return_class(baseclass, override_fields, xpath_prefix=None,
            override_xpaths={}):
    """
    Define a new return class which extends the specified baseclass and
    overrides the specified fields.

    :param baseclass: the baseclass to be extended; expected to be an instance of XmlObject
    :param override_fields: dictionary of field, list of nodefields - in the format of partial_fields
    	or additional_fields, as genreated by QuerySet.only or QuerySet.also
    :param xpath_prefix: optional, should only be used when recursing.  By default, the xpath
    	for a constructed node is assumed to be the same as the field name; for sub-object fields,
        this parameter is used to pass the prefix in for creating the sub-object class.
    :param override_xpaths: dictionary of field name and xpaths to use, based on
        the constructed xml being returned; most likely generated by 
        :meth:`Xquery.get_return_xpaths`.
    """

    # NOTE: this class is tested indirectly via the QuerySet also and only functions,
    # but it is *not* tested directly.    
    
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
            if name == 'last_modified':     # special case field
                field_type = DateField
            elif fields is None or isinstance(fields, basestring):
                field_type = StringField	# handle special cases like fulltext score
            else:
                field_type = type(fields[-1])

            # by default, assume xpath is field name
            xpath = name
            fieldname = name
            if xpath_prefix:
                xpath = "__".join((xpath_prefix, name))
                fieldname = "__".join((xpath_prefix, name))
                
            # if an override xpath is specified for this field, use that
            if fieldname in override_xpaths:
                xpath = override_xpaths[fieldname]

            #TODO: create a clone function for nodefield that takes an xpath
            # (this should make field-type instantiation more reliable and flexible)
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
                                        xpath_prefix=prefix, override_xpaths=override_xpaths)
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
    special_fields =  ['fulltext_score', 'last_modified', 'hash',
        'document_name', 'collection_name']

    
    def __init__(self, xpath=None, collection=None):
        if xpath is not None:
            self.xpath = xpath

        # remove leading / from collection name (if any)
        self.collection = collection.lstrip('/') if collection is not None else None
        self.filters = []
        # sort information - field to sort on, ascending/descending
        self.order_by = None
        self.order_mode = None
        # also/only fields
        self.return_fields = {}
        self.additional_return_fields = {}
        # start/end values for subsequence
        self.start = 0
        self.end = None
        self._distinct = False
        # return field / xpath details for constructed xquery return
        self.return_xpaths = []
        self._return_field_count = 1

    def __str__(self):
        return self.getQuery()

    def getCopy(self):
        xq = Xquery(xpath=self.xpath, collection=self.collection)
        xq.filters += self.filters
        xq.order_by = self.order_by
        xq.order_mode = self.order_mode
        xq._distinct = self._distinct
        # return *copies* of dictionaries, not references to the ones in this object!
        xq.return_fields = self.return_fields.copy()
        xq.additional_return_fields = self.additional_return_fields.copy()
        xq.return_xpaths = self.return_xpaths
        xq._return_field_count = self._return_field_count
        return xq

    def getQuery(self):
        """
        Generate and return xquery based on configured filters, sorting, return fields.
        Returns xpath or FLOWR XQuery if required based on sorting and return
        """
        xpath_parts = []
        if self.collection is not None:
            # if a collection is specified, add it it to the top-level query xpath
            # -- prep_xpath handles logic for top-level xpath with multiple components, e.g. foo|bar 
            collection_xquery = 'collection("/db/%s")' % self.collection
            xpath_parts.append(self.prep_xpath(self.xpath, context=collection_xquery))
        else:
            xpath_parts.append(self.xpath)
            
        xpath_parts += [ '[%s]' % (f,) for f in self.filters ]

        xpath = ''.join(xpath_parts)
        # requires FLOWR instead of just XQuery  (sort, customized return, etc.)
        if self.order_by or self.return_fields or self.additional_return_fields:
            # NOTE: using constructed xpath, with collection filter (if collection specified)
            flowr_for = 'for %s in %s' % (self.xq_var, xpath)

            # define any special fields that have been requested
            let = []
            for field in self.special_fields:
                if field == self.order_by or field in self.return_fields \
                        or field in self.additional_return_fields:
                    # determine how to calculate the value of the requested field
                    if field == 'fulltext_score':
                        val = 'ft:score(%s)' % self.xq_var
                    elif field == 'hash':
                        val = 'util:hash(%s, "SHA-1")' % self.xq_var
                    elif field == 'document_name':
                        val = 'util:document-name(%s)' % self.xq_var
                    elif field == 'collection_name':
                        val = 'util:collection-name(%s)' % self.xq_var
                    elif field == 'document_name':
                        val = 'util:document-name(%s)' % self.xq_var
                    elif field == 'last_modified':
                        val = 'xmldb:last-modified(util:collection-name(%(var)s), util:document-name(%(var)s))' % \
                            {'var': self.xq_var }
                    # define an xquery variable with the same name as the special field
                    let.append('let $%s := %s' % (field, val))

            flowr_let = '\n'.join(let)
            
            # for now, assume sort relative to root element
            if self.order_by:                
                if self.order_by in self.special_fields:
                    order_field = '$%s' % self.order_by
                else:
                    order_field = self.prep_xpath(self.order_by)
                flowr_order = 'order by %s %s' % (order_field, self.order_mode)
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

    def sort(self, field, ascending=True):
        "Add ordering to xquery; sort field assumed relative to base xpath"
        # todo: support multiple sort fields
        self.order_by = field
        self.order_mode = 'ascending' if ascending else 'descending'

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
        """Only return the specified fields.  Fields should be a dictionary of
        {'field name' : 'xpath'}."""
        self.return_fields.update(fields)

    def return_also(self, fields):
        """Return additional specified fields.  Fields should be a dictionary of
        {'field name' : 'xpath'}.
        
        Not compatible with :meth:`return_only`."""
        self.additional_return_fields.update(fields)

    def _constructReturn(self):
        """Construct the return portion of a FLOWR xquery."""
        
        if self.return_fields or self.additional_return_fields:
            # constructed return result with partial or additional content

            # get a return element name to wrap the results
            return_el = self._return_name_from_xpath(parse(self.xpath))

            # reset any return fields that have been previously calculated
            self._return_field_count = 1
            self.return_xpaths = []

            # returns for only/also fields are constructed almost exactly the same
            if self.return_fields:
                rblocks = []
            elif self.additional_return_fields:
                # return everything under matched node - all attributes, all nodes
                rblocks = ["{%s/@*}" % self.xq_var, "{%s/node()}" % self.xq_var]
                
            fields = dict(self.return_fields, **self.additional_return_fields)
            for name, xpath in fields.iteritems():
                # special cases
                if name in self.special_fields:
                    # reference any special fields requested as xquery variables
                    rblocks.append('<%(name)s>{$%(name)s}</%(name)s>' % {'name': name })
                else:
                    rblocks.append(self.prep_xpath(xpath, return_field=True))
            return 'return <%s>\n ' % (return_el)  + '\n '.join(rblocks) + '\n</%s>' % (return_el)
        else:
            # return entire node, no constructed return
            return 'return %s' % self.xq_var

    def _return_name_from_xpath(self, parsed_xpath):
        "Generate a top-level return element name based on the xpath."
        if isinstance(parsed_xpath, ast.Step):
            # if this is a step, just use the node test
            return parsed_xpath.node_test
        elif isinstance(parsed_xpath, ast.BinaryExpression):
            # binary expression like node()|node() - recurse on right hand portion
            return self._return_name_from_xpath(parsed_xpath.right)
        elif isinstance(parsed_xpath, ast.AbsolutePath):
            # absolute path like //a - recurse on relative portion
            return self._return_name_from_xpath(parsed_xpath.relative)

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

    def prep_xpath(self, xpath, context=None, return_field=False, parsed=False):
        """Prepare an xpath for use in an xquery.

        :param xpath: xpath as string or parsed by :meth:`eulcore.xpath.parse`
        :param context: optional context to add to xpaths; by default, the current
            xquery variable will be used
        :param return_field: xpath will be used as a return field; it will have
            additional node wrapping, and a return-field xpath will be calculated
            and stored for use in :meth:`get_return_xpaths`
        :param parsed: boolean flag to indicate if xpath has already been parsed
        :rtype: string
        """
        # common xpath clean-up before handing off to exist
        parsed_xpath = xpath if parsed else parse(xpath)
        if context is None:
            context = self.xq_var

        if isinstance(parsed_xpath, ast.BinaryExpression) and parsed_xpath.op == '|': 
            # binary OR expression - prep the two expressions and put them back together
            xpath_str = '%(left)s%(op)s%(right)s' % {
                    'op': parsed_xpath.op,
                    'left': self.prep_xpath(parsed_xpath.left, parsed=True, context=context),
                    'right': self.prep_xpath(parsed_xpath.right, parsed=True, context=context),
                    'var': self.xq_var
                    }
            # xquery context variable has been added to individual portions and
            # should not be added again
            context_path = None
        # determine context needed relative to xquery variable
        elif isinstance(parsed_xpath, ast.AbsolutePath):
            # for an absolute path, (e.g., //node or /node), we need $n(xpath)
            context_path = context
        elif isinstance(parsed_xpath, ast.FunctionCall):
            # function call - the function itself needs no context, but
            # any arguments that are node tests should be prepped
            context_path = ''
            for i in range(len(parsed_xpath.args)):
                arg = parsed_xpath.args[i]
                if isinstance(arg, ast.AbbreviatedStep) or isinstance(arg, ast.Step):
                    # prep_xpath returns string, but function arg needs to be parsed
                    parsed_xpath.args[i] = parse(self.prep_xpath(arg, parsed=True))
        else:
            # for a relative path, we need $n/(xpath)
            context_path = "%s/" % context
            
        # FIXME: other possible cases?
        
        if context_path is not None:
            xpath_str = "%(context)s%(xpath)s" % {'context': context_path,
                                                  'xpath': serialize(parsed_xpath) }

        if return_field:
            xpath_str = "<field>{%s}</field>" % xpath_str
            # get xpath for field as it will be returned
            self.return_xpaths.append(self._return_field_xpath(parsed_xpath))
            self._return_field_count += 1

        return xpath_str

    def _return_field_xpath(self, xpath):
        if isinstance(xpath, ast.Step):
            return "field[%d]/%s" % (self._return_field_count, serialize(xpath))
        elif isinstance(xpath, ast.BinaryExpression):
            if xpath.op == '|':
                return "%(left)s|%(right)s" % {
                    'left': self._return_field_xpath(xpath.left),
                    'right': self._return_field_xpath(xpath.right)
                    }
            if xpath.op in ('/', '//'):
                return self._return_field_xpath(xpath.right)
        elif isinstance(xpath, ast.FunctionCall):
            # for a function call, the field itself should be all the xpath needed
            return "field[%d]" % self._return_field_count
        
        # FIXME: other cases?
        return None     # FIXME: is there any sane fall-back return?

    def get_return_xpaths(self):
        """Generate a dictionary of xpaths to match the results as they will be
        returned in a constructed return result (when return fields have
        been specified by :meth:`return_also` or :meth:`return_only`).
        
        :returns: dictionary keyed on field names from argument passed to
            :meth:`return_only` or :meth:`return_also`
        :rtype: dict
        """
        fields = dict(self.return_fields, **self.additional_return_fields)
        xpaths = {}
        i = 0
        for name in fields.keys():
            if name in ['fulltext_score', 'last_modified', 'hash', 'document_name', 'collection_name']:
                xpaths[name] = name
            else:
                xpaths[name] = self.return_xpaths[i]
                i += 1
        return xpaths

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
