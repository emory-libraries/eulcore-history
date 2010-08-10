# file django\soap\app.py
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
