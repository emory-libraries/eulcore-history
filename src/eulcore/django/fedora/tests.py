from StringIO import StringIO
import unittest

from django.template import Context, Template
from eulcore.fedora.util import RequestFailed, PermissionDenied

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
