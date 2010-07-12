# based on code from http://djangosnippets.org/snippets/254/
from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.template import RequestContext
from django.template.loader import get_template
from django.utils.http import urlquote

def user_passes_test_with_403(test_func, login_url=None):
    """
    View decorator that checks to see if the user passes the specified test.
    See :meth:`django.contrib.auth.decorators.user_passes_test`.

    Anonymous users will be redirected to login_url, while logged in users that
    fail the test will be given a 403 error.  In the case of a 403, the function
    will render the **403.html** template.
    """
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL
    def _dec(view_func):
        @wraps(view_func)
        def _checklogin(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            elif not request.user.is_authenticated():
                return HttpResponseRedirect('%s?%s=%s' % (login_url,
                            REDIRECT_FIELD_NAME, urlquote(request.get_full_path())))
            else:
                tpl = get_template('403.html')
                return HttpResponseForbidden(tpl.render(RequestContext(request)))
        return _checklogin
    return _dec

def permission_required_with_403(perm, login_url=None):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled, redirecting to the login page or rendering a 403 as necessary.

    See :meth:`django.contrib.auth.decorators.permission_required`.
    """
    return user_passes_test_with_403(lambda u: u.has_perm(perm), login_url=login_url)
