# based on http://www.djangosnippets.org/snippets/979/
# see also:
#   - http://trac.optio.webfactional.com/wiki/soaplib
#   - http://www.lonelycode.com/2008/12/19/django-python-and-the-sorry-state-of-web-services/

from django.http import HttpResponse
from soaplib.wsgi_soap import SimpleWSGISoapApp

# not used locally, but exported for clients:
from soaplib.serializers import primitive as soap_types
from soaplib.service import soapmethod

class DjangoSoapApp(SimpleWSGISoapApp):
    def __call__(self, request):
        django_response = HttpResponse()
        def start_response(status, headers):
            status, reason = status.split(' ', 1)
            django_response.status_code = int(status)
            for header, value in headers:
                django_response[header] = value
        response = super(DjangoSoapApp, self).__call__(request.META, start_response)
        django_response.content = "\n".join(response)

        return django_response
