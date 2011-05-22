# file django/forms/tests.py
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

import re
from recaptcha.client import captcha
import unittest

from django.conf import settings
from django.forms import ValidationError

from eullocal.django.forms import captchafield


class MockCaptcha:
    'Mock captcha client to allow testing without querying captcha servers'
    response = captcha.RecaptchaResponse(True)
    submit_args = {}
    display_arg = None

    def displayhtml(self, pubkey):
        self.display_arg = pubkey
        return ''

    def submit(self, challenge, response, private_key, remote_ip):
        self.submit_args = {'challenge': challenge, 'response': response,
            'private_key': private_key, 'remote_ip': remote_ip}
        return self.response

class MockCaptchaTest(unittest.TestCase):

    captcha_module = captchafield

    def setUp(self):
        # swap out captcha with mock
        self._captcha = self.captcha_module.captcha
        self.captcha_module.captcha = MockCaptcha()
        # set required captcha configs
        self._captcha_private_key = getattr(settings, 'RECAPTCHA_PRIVATE_KEY', None)
        self._captcha_public_key = getattr(settings, 'RECAPTCHA_PUBLIC_KEY', None)
        self._captcha_opts = getattr(settings, 'RECAPTCHA_OPTIONS', None)
        settings.RECAPTCHA_PRIVATE_KEY = 'mine & mine alone'
        settings.RECAPTCHA_PUBLIC_KEY = 'anyone can see this'
        settings.RECAPTCHA_OPTIONS = {}

    def tearDown(self):
        # restore real captcha
        self.captcha_module.captcha = self._captcha
        # restore captcha settings
        if self._captcha_private_key is None:
            delattr(settings, 'RECAPTCHA_PRIVATE_KEY')
        else:
            settings.RECAPTCHA_PRIVATE_KEY = self._captcha_private_key
        if self._captcha_public_key is None:
            delattr(settings, 'RECAPTCHA_PUBLIC_KEY')
        else:
            settings.RECAPTCHA_PUBLIC_KEY = self._captcha_public_key
        if self._captcha_opts is None:
            delattr(settings, 'RECAPTCHA_OPTIONS')
        else:
            settings.RECAPTCHA_OPTIONS = self._captcha_opts


class ReCaptchaWidgetTest(MockCaptchaTest):

    def test_render(self):
        widget = captchafield.ReCaptchaWidget()
        html = widget.render('captcha', None)
        self.assertTrue(html)
        self.assertEqual(settings.RECAPTCHA_PUBLIC_KEY, self.captcha_module.captcha.display_arg,
            'captcha challenge should be generated with public key from settings')
        self.assert_('<script' not in html,
            'widget output should not include <script> tag when no render options are set')

        widget = captchafield.ReCaptchaWidget(attrs={'theme': 'white'})
        html = widget.render('captcha', None)
        self.assert_('<script' in html,
            'widget output should include <script> tag when no render options are set')
        self.assert_('var RecaptchaOptions = {"theme": "white"};' in html,
            'recaptcha options should be generated from widget attributes')

        settings.RECAPTCHA_OPTIONS = {'lang': 'fr'}
        widget = captchafield.ReCaptchaWidget()
        html = widget.render('captcha', None)
        self.assert_('var RecaptchaOptions = {"lang": "fr"};' in html,
            'recaptcha options should be generated from RECAPTCHA_OPTIONS in settings')

        widget = captchafield.ReCaptchaWidget(attrs={'lang': 'en'})
        html = widget.render('captcha', None)
        self.assert_('var RecaptchaOptions = {"lang": "en"};' in html,
            'widget attributes should supercede recaptcha options from RECAPTCHA_OPTIONS in settings')

class ReCaptchaFieldTest(MockCaptchaTest):

    def test_clean(self):
        field = captchafield.ReCaptchaField()

        data = {'challenge': 'knock knock', 'response': 'who\'s there?',
            'remote_ip': '127.0.0.1'}
        field.clean(data)
        # check that captcha was submitted correctly
        self.assertEqual(data['challenge'],
            captchafield.captcha.submit_args['challenge'])
        self.assertEqual(data['response'],
            captchafield.captcha.submit_args['response'])
        self.assertEqual(settings.RECAPTCHA_PRIVATE_KEY,
            captchafield.captcha.submit_args['private_key'])
        self.assertEqual(data['remote_ip'], self.captcha_module.captcha.submit_args['remote_ip'])

        # simulate invalid captcha response
        self.captcha_module.captcha.response.is_valid = False
        self.captcha_module.captcha.response.err_code = 'incorrect-captcha-sol'
        self.assertRaises(ValidationError, field.clean, data)

        # other error
        self.captcha_module.captcha.response.err_code = 'invalid-referrer'
        self.assertRaises(ValidationError, field.clean, data)

        # restore success response
        self.captcha_module.captcha.response.is_valid = True
        self.captcha_module.captcha.response.err_code = None
