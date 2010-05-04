# functions for posting multipart form data
# this code is a combination of:
#  - http://code.activestate.com/recipes/146306/
#  - urllib3.filepost.py    http://code.google.com/p/urllib3/

import httplib
import mimetypes
import string
import random

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

def post_multipart(host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)
    h = httplib.HTTP(host)
    h.putrequest('POST', selector)
    h.putheader('content-type', content_type)
    h.putheader('content-length', str(len(body)))
    h.endheaders()
    h.send(body)
    errcode, errmsg, headers = h.getreply()
    return h.file.read()

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
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

# generate a random boundary character string
def generate_boundary():
    return ''.join(random.choice(string.hexdigits[:16]) for x in range(32))