# custom HTTP Responses that Django doesn't provide

from django.http import HttpResponse, HttpResponseRedirect

class HttpResponseSeeOtherRedirect(HttpResponseRedirect):
    """Variant of Django's :class:`django.http.HttpResponseRedirect`.  Redirect
    with status code 303, 'See Other'.  This code indicates that the redirected
    content is not a replacement for the requested content, but a different resource.
    """
    status_code = 303
    
class HttpResponseUnauthorized(HttpResponse):
    '''Variant of Django's :class:`django.http.HttpResponse` for status code
    401 'Unauthorized'.  Takes a single required argument of expected
    authentication method (currently only supports one) to populate the
    WWW-Authenticate header that is required in a 401 response.  Example use::

        HttpResponseUnauthorized('my realm')

    '''
    status_code = 401

    def __init__(self, realm='Restricted Access'):
        HttpResponse.__init__(self)
        self['WWW-Authenticate'] = 'Basic realm="%s"' % realm

class HttpResponseUnsupportedMediaType(HttpResponse):
    """Variant of Django's :class:`django.http.HttpResponse` with status
    code 415 Unsupported Media Type.
    """
    status_code = 415