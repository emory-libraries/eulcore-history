from django.conf import settings
from eulcore.existdb import db
from django.core.paginator import Paginator, InvalidPage, EmptyPage, Page

ExistDBException = db.ExistDBException

# this is a wrapper for a django-unaware existdb class
# initializes ExistDB object based on django settings

class ExistDB(db.ExistDB):

    def __init__(self, resultType=None):
        db.ExistDB.__init__(self, resultType=resultType,
                            server_url=settings.EXISTDB_SERVER_URL)

class ResultPaginator(Paginator):
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
