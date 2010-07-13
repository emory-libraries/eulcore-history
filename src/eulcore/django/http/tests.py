from django.http import HttpResponse, HttpRequest
from django.test import TestCase

from eulcore.django.http import content_negotiation

def html_view(request):
    "a simple view for testing content negotiation"
    return "HTML"

def xml_view(request):
    return "XML"

class ContentNegotiationTest(TestCase):
    # known browser accept headers - taken from https://developer.mozilla.org/en/Content_negotiation
    FIREFOX = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    CHROME = 'application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5'
    # same Accept header used by both Safari and Google Chrome
    IE8 = 'image/jpeg, application/x-ms-application, image/gif, application/xaml+xml, image/pjpeg, application/x-ms-xbap, application/x-shockwave-flash, application/msword, */*'

    def setUp(self):
        self.request = HttpRequest()
        
        # add content negotiation to test view defined above for testing
        decorator = content_negotiation({'application/xml': xml_view})
        self.negotiated_view = decorator(html_view)

    def test_default(self):
        # no accept header specified - should use default view
        response = self.negotiated_view(self.request)
        self.assertEqual("HTML", response)

    def test_html(self):
        self.request.META['HTTP_ACCEPT'] = 'text/html, application/xhtml+xml'
        response = self.negotiated_view(self.request)
        self.assertEqual("HTML", response)

    def test_xml(self):
        self.request.META['HTTP_ACCEPT'] = 'application/xml'
        response = self.negotiated_view(self.request)
        self.assertEqual("XML", response)

    def test_browsers(self):
        # some browsers request things oddly so they might not get what they actually want
        # confirm that these known browsers get the default text/html content instead of application/xml
        self.request.META['HTTP_ACCEPT'] = self.FIREFOX
        response = self.negotiated_view(self.request)
        self.assertEqual("HTML", response,
            "got HTML content with Firefox Accept header")

        self.request.META['HTTP_ACCEPT'] = self.CHROME
        response = self.negotiated_view(self.request)
        self.assertEqual("HTML", response,
            "got HTML content with Chrome/Safari Accept header")

        self.request.META['HTTP_ACCEPT'] = self.IE8
        response = self.negotiated_view(self.request)
        self.assertEqual("HTML", response,
            "got HTML content with IE8 Accept header")

    def test_function_wrapping(self):
        # make sure we play nice for document
        self.assertEqual(self.negotiated_view.__doc__, html_view.__doc__,
            "decorated method docstring matches original method docstring")
        self.assertEqual(self.negotiated_view.__name__, html_view.__name__,
            "decorated method name matches original method name")
