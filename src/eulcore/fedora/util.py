import httplib
from datetime import datetime
from dateutil.tz import tzutc
import mimetypes
import random
import string
from cStringIO import StringIO

from base64 import b64encode
from urlparse import urljoin, urlsplit

from rdflib import URIRef, Graph

from eulcore import xmlmap

# functions for posting multipart form data
# this code is a combination of:
#  - http://code.activestate.com/recipes/146306/
#  - urllib3.filepost.py    http://code.google.com/p/urllib3/

ENCODE_TEMPLATE= """--%(boundary)s
Content-Disposition: form-data; name="%(name)s"

%(value)s
""".replace('\n','\r\n')

ENCODE_TEMPLATE_FILE = """--%(boundary)s
Content-Disposition: form-data; name="%(name)s"; filename="%(filename)s"
Content-Type: %(contenttype)s

%(value)s
--%(boundary)s--

""".replace('\n','\r\n')

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """    
    BOUNDARY = generate_boundary()

    body = ""

    # NOTE: Every non-binary possibly-unicode variable must be casted to str()
    # because if a unicode value pollutes the `body` string, then all of body
    # will become unicode. Appending a binary file string to a unicode string
    # will cast the binary data to unicode, which will raise an encoding
    # exception. Long story short, we want to stick to plain strings.
    # This is not ideal, but if anyone has a better method, I'd love to hear it.

    for key, value in fields:
        body += ENCODE_TEMPLATE % {
                        'boundary': BOUNDARY,
                        'name': str(key),
                        'value': str(value)
                    }
    for (key, filename, value) in files:
        body += ENCODE_TEMPLATE_FILE % {
                    'boundary': BOUNDARY,
                    'name': str(key),
                    'value': str(value),
                    'filename': str(filename),
                    'contenttype': str(get_content_type(filename))
                    }

    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    if filename:
        guesses = mimetypes.guess_type(filename)
        if guesses:
            return guesses[0]
    return 'application/octet-stream'

# generate a random boundary character string
def generate_boundary():
    return ''.join(random.choice(string.hexdigits[:16]) for x in range(32))


# utilities for making HTTP requests to fedora

def auth_headers(username, password):
    "Build HTTP basic authentication headers"
    if username and password:
        token = b64encode('%s:%s' % (username, password))
        return { 'Authorization': 'Basic ' + token }
    else:
        return {}

class RequestFailed(IOError):
    def __init__(self, response):
        super(RequestFailed, self).__init__('%d %s' % (response.status, response.reason))
        self.code = response.status
        self.reason = response.reason


class RequestContextManager(object):
    # used by HTTP APIs to close http connections automatically and
    # ease connection creation
    def __init__(self, method, url, body=None, headers=None, throw_errors=True):
        self.method = method
        self.url = url
        self.body = body
        self.headers = headers
        self.throw_errors = throw_errors

    def __enter__(self):
        urlparts = urlsplit(self.url)
        if urlparts.scheme == 'http':
            connection = httplib.HTTPConnection(urlparts.hostname, urlparts.port)
        elif urlparts.scheme == 'https':
            connection = httplib.HTTPSConnection(urlparts.hostname, urlparts.port)
        self.connection = connection

        try:
            connection.request(self.method, self.url, self.body, self.headers)
            response = connection.getresponse()
            # FIXME: handle 3xx
            if response.status >= 400 and self.throw_errors:
                raise RequestFailed(response)
            return response
        except:
            connection.close()
            raise

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.connection.close()


# wrap up all of our common aspects of accessing data over HTTP, from
# authentication to http/s switching to connection management to relative
# path resolving. sorta like urllib2 with extras.
class RelativeOpener(object):
    def __init__(self, base_url, username=None, password=None):
        self.base_url = base_url
        self.username = username
        self.password = password

    def _auth_headers(self):
        if self.username:
            token = b64encode('%s:%s' % (self.username, self.password))
            return { 'Authorization': 'Basic ' + token }
        else:
            return {}

    def absurl(self, rel_url):
        return urljoin(self.base_url, rel_url)

    def _abs_open(self, method, abs_url, body=None, headers={}, throw_errors=True):
        headers = headers.copy()
        headers.update(self._auth_headers())
        return RequestContextManager(method, abs_url, body, headers, throw_errors)

    def open(self, method, rel_url, body=None, headers={}, throw_errors=True):
        abs_url = self.absurl(rel_url)
        return self._abs_open(method, abs_url, body, headers,
                              throw_errors=throw_errors)

    def read(self, rel_url, data=None):
        method = 'GET'
        if data is not None:
            method = 'POST'
        abs_url = self.absurl(rel_url)
        with self._abs_open(method, abs_url, data) as fobj:
            return fobj.read(), abs_url


def parse_rdf(data, url, format=None):
    fobj = StringIO(data)
    id = URIRef(url)
    graph = Graph(identifier=id)
    if format is None:
        graph.parse(fobj)
    else:
        graph.parse(fobj, format=format)
    return graph

def parse_xml_object(cls, data, url):
    doc = xmlmap.parseString(data, url)
    return cls(doc)

def datetime_to_fedoratime(datetime):
    # format a date-time in a format fedora can handle
    # make sure time is in UTC, since the only time-zone notation Fedora seems able to handle is 'Z'
    utctime = datetime.astimezone(tzutc())      
    return utctime.strftime('%Y-%m-%dT%H:%M:%S') + '.%03d' % (utctime.microsecond/1000) + 'Z'


def fedoratime_to_datetime(rep):
    if rep.endswith('Z'):       
        rep = rep[:-1]      # strip Z for parsing
        tz = tzutc()
        # strptime creates a timezone-naive datetime
        dt = datetime.strptime(rep, '%Y-%m-%dT%H:%M:%S.%f')
        # use the generated time to create a timezone-aware
        return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, tz)
    else:
        raise Exception("Cannot parse '%s' as a Fedora datetime" % rep)
