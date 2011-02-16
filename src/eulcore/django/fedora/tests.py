from os import path
from StringIO import StringIO
import unittest

from django.conf import settings
from django.http import Http404
from django.template import Context, Template

from eulcore.fedora.util import RequestFailed, PermissionDenied
from eulcore.fedora.models import DigitalObject, Datastream, FileDatastream
from eulcore.django.fedora.server import Repository
from eulcore.django.fedora.views import raw_datastream

class MockFedoraResponse(StringIO):
    # The simplest thing that can possibly look like a Fedora response to
    # eulcore.fedora.util
    def __init__(self, status=500, reason='Cuz I said so',
                 mimetype='text/plain', content=''):
        StringIO.__init__(self, content)
        self.status = status
        self.reason = reason
        self.mimetype = mimetype
        self.msg = self # for self.msg.gettype()

    def gettype(self):
        return self.mimetype

class MockFedoraObject(object):
    # not even a close approximation, just something we can force to raise
    # interesting exceptions
    def __init__(self):
        self._value = 'sample text'

    def value(self):
        if isinstance(self._value, Exception):
            raise self._value
        return self._value

        
class TemplateTagTest(unittest.TestCase):
    def test_parse_fedora_access(self):
        TEMPLATE_TEXT = """
            {% load fedora %}
            {% fedora_access %}
                {{ test_obj.value }}
            {% permission_denied %}
                permission fallback
            {% fedora_failed %}
                connection fallback
            {% end_fedora_access %}
        """
        t = Template(TEMPLATE_TEXT)
        test_obj = MockFedoraObject()
        ctx = Context({'test_obj': test_obj})

        val = t.render(ctx)
        self.assertEqual(val.strip(), 'sample text')

        response = MockFedoraResponse(status=401)
        test_obj._value = PermissionDenied(response) # force test_obj.value to fail
        val = t.render(ctx)
        self.assertEqual(val.strip(), 'permission fallback')

        response = MockFedoraResponse()
        test_obj._value = RequestFailed(response) # force test_obj.value to fail
        val = t.render(ctx)
        self.assertEqual(val.strip(), 'connection fallback')


class SimpleDigitalObject(DigitalObject):
    CONTENT_MODELS = ['info:fedora/example:SimpleCModel' ]

    # extend digital object with datastreams for testing
    text = Datastream("TEXT", "Text datastream", defaults={
            'mimetype': 'text/plain',
        })
    image = FileDatastream('IMAGE', 'managed binary image datastream', defaults={
                'mimetype': 'image/png'
        })

class FedoraViewsTest(unittest.TestCase):


    def setUp(self):
        # load test object to test views with
        repo = Repository()
        self.obj = repo.get_object(type=SimpleDigitalObject)
        self.obj.dc.content.title = 'test object for generic views'
        self.obj.text.content = 'sample plain-text content'
        img_file = path.join(settings.FEDORA_FIXTURES_DIR, 'test.png')
        self.obj.image.content = open(img_file)
        # force datastream checksums so we can test response headers
        for ds in [self.obj.dc, self.obj.rels_ext, self.obj.text, self.obj.image]:
            ds.checksum_type = 'MD5'
        self.obj.save()

    def tearDown(self):
        self.obj.api.purgeObject(self.obj.pid)

    def test_raw_datastream(self):        
        # DC
        response = raw_datastream('rqst', self.obj.pid, 'DC')
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for raw_datastream view of DC' \
                % (expected, got))
        expected, got = 'text/xml', response['Content-Type']
        self.assertEqual(expected, got,
            'Expected %s but returned %s for mimetype on raw_datastream view of DC' \
                % (expected, got))
        self.assertEqual(self.obj.dc.checksum, response['ETag'],
            'datastream checksum should be set as ETag header in the response')
        self.assertFalse(response.has_header('Content-MD5'))
        self.assert_('<dc:title>%s</dc:title>' % self.obj.dc.content.title in response.content)

        # RELS-EXT
        response = raw_datastream('rqst', self.obj.pid, 'RELS-EXT')
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for raw_datastream view of RELS-EXT' \
                % (expected, got))
        expected, got = 'application/rdf+xml', response['Content-Type']
        self.assertEqual(expected, got,
            'Expected %s but returned %s for mimetype on raw_datastream view of RELS-EXT' \
                % (expected, got))

        # TEXT  (non-xml content)
        response = raw_datastream('rqst', self.obj.pid, 'TEXT')
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for raw_datastream view of TEXT' \
                % (expected, got))
        expected, got = 'text/plain', response['Content-Type']
        self.assertEqual(expected, got,
            'Expected %s but returned %s for mimetype on raw_datastream view of TEXT' \
                % (expected, got))
        # non-xml datastreams should have content-md5 & content-length headers
        self.assertEqual(self.obj.text.checksum, response['Content-MD5'],
            'datastream checksum should be set as Content-MD5 header in the response')
        self.assertEqual(len(self.obj.text.content), int(response['Content-Length']))

        # IMAGE (binary content)
        response = raw_datastream('rqst', self.obj.pid, 'IMAGE')
        expected, got = 200, response.status_code
        self.assertEqual(expected, got,
            'Expected %s but returned %s for raw_datastream view of IMAGE' \
                % (expected, got))
        expected, got = 'image/png', response['Content-Type']
        self.assertEqual(expected, got,
            'Expected %s but returned %s for mimetype on raw_datastream view of IMAGE' \
                % (expected, got))
        # non-xml datastreams should have content-md5 & content-length headers
        self.assertEqual(self.obj.image.checksum, response['Content-MD5'],
            'datastream checksum should be set as Content-MD5 header in the response')
        self.assertTrue(response.has_header('Content-Length'),
            'content-length header should be set in the response for binary datastreams')

        # non-existent datastream should 404
        self.assertRaises(Http404, raw_datastream, 'rqst', self.obj.pid, 'BOGUS-DSID')        

        # non-existent record should 404
        self.assertRaises(Http404, raw_datastream, 'rqst', 'bogus-pid:1', 'DC')

        # check type handling?
        