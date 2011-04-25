# file django/existdb/db.py
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

import urlparse
import warnings

from django.conf import settings
from eulcore.existdb.db import ExistDB as BaseExistDB
from eulcore.existdb.db import ExistDBException
from django.core.paginator import Paginator, Page

__all__ = ['ExistDB', 'ResultPaginator']

#ExistDBException = db.ExistDBException

class ExistDB(BaseExistDB):

    """Connect to an eXist database configured by ``settings.py``.

    :param resultType: The class to use for returning :meth:`query` results;
      defaults to :class:`eulcore.existdb.QueryResult`.
                       
    :param timeout: Connection timeout setting, if any.  If none is
      specified, this class will look for a ``EXISTDB_TIMEOUT``
      configuration in django settings.

    This class is a simple wrapper for :class:`eulcore.existdb.db.ExistDB`,
    getting the server_url from the Django settings file instead of in an
    argument.

    """

    def __init__(self, resultType=None, timeout=None):
        if timeout is None:
            timeout = getattr(settings, 'EXISTDB_TIMEOUT', None)

        
        BaseExistDB.__init__(self, resultType=resultType,
                            server_url=self._get_exist_url(),
                            timeout=timeout)

    def _get_exist_url(self):
        # determine what exist url to use based on django settings
        
        # don't worry about errors on this one - if it isn't set, this should fail
        exist_url = settings.EXISTDB_SERVER_URL
        
        # former syntax had credentials in the server url; warn about the change
        if '@' in exist_url:
            warnings.warn("""EXISTDB_SERVER_URL should not include eXist user or password information.  You should update your django settings to use EXISTDB_SERVER_USER and EXISTDB_SERVER_PASSWORD.""")

        # look for username & password
        username = getattr(settings, 'EXISTDB_SERVER_USER', None)
        password = getattr(settings, 'EXISTDB_SERVER_PASSWORD', None)
        
        # if username or password are configured, add them to the url
        if username or password:
            # split the url into its component parts
            urlparts = urlparse.urlsplit(exist_url)
            # could have both username and password or just a username
            if username and password:
                prefix = '%s:%s' % (username, password)
            else:
                prefix = username
            # prefix the network location with credentials
            netloc = '%s@%s' % (prefix, urlparts.netloc)
            # un-split the url with all the previous parts and modified location
            exist_url = urlparse.urlunsplit((urlparts.scheme, netloc, urlparts.path,
                                            urlparts.query, urlparts.fragment))

        return exist_url



class ResultPaginator(Paginator):

    """Paginate results from a :class:`eulcore.existdb.query.QuerySet`.

    This class extends :class:`django.core.paginator.Paginator` to deal
    effectively with :class:`~eulcore.existdb.db.QueryResult` objects.

    :param qry_result: a :class:`~eulcore.existdb.db.QueryResult` object
                       providing metadata about the query result

    Other arguments and methods are as for a standard
    :class:`~django.core.paginator.Paginator`.

    """

    def __init__(self, qry_result, result_list, orphans=0, allow_empty_first_page=False):
        self._qry_result = qry_result
        Paginator.__init__(self, result_list, self._qry_result.count, orphans, allow_empty_first_page)

    def _get_count(self):
        "Returns the total number of hits, across all pages."
        self._count = self._qry_result.hits
        return self._count
    count = property(_get_count)

    def page(self, number):
        "Returns a Page object for the given exist result set."
        # Make sure page requested is an int. If not, deliver first page.
        try:
            page = int(number)
        except ValueError:
            page = 1

        #if page request exceeds max pages return last page
        if (page > self.num_pages):
            page = self.num_pages
        elif page < 1:
            page = 1

        #paginator assumes all data was returned however eXist returns data in chunks
        #so we always want all results 
        return Page(self.object_list, page, self)
