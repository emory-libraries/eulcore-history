# file django/non_app_tests.py
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


# Add tests here for code that is not part of a django application.
# These tests can be run using test_django_non_apps.py
# Tests here are also included when running test_all.py

import logging

from django.contrib import messages
from django.test import TestCase
from eulcore.django import log

mock_messages = []
def mock_add_message(rqst, level, message):
    mock_messages.append((level, message))

log.messages.add_message = mock_add_message

class DjangoMessageHandlerTest(TestCase):
    # very simple mock add_message function (avoid using django messaging infrastructure for tests)
    
    def _log_record(self, level, text):
        # simple method to generate a logRecord to pass to handler emit function
        return logging.LogRecord('test', level, __name__, 0,
            text, [], [])

    def setUp(self):
        self.mh = log.DjangoMessageHandler('request')

    def test_emit_info(self):
        log_msg = 'for your information'
        self.mh.emit(self._log_record(logging.INFO, log_msg))
        level, text = mock_messages[-1]
        self.assertEqual(messages.INFO, level,
            'INFO log level converted to django messages INFO')
        self.assertEqual(log_msg, text,
            'log message stored as django message text')

    def test_emit_warning(self):
        log_msg = 'this is your last warning'
        self.mh.emit(self._log_record(logging.WARNING, log_msg))
        level, text = mock_messages[-1]
        self.assertEqual(messages.WARNING, level,
            'WARNING log level converted to django messages WARNING')
        self.assertEqual(log_msg, text,
            'log message stored as django message text')

    def test_emit_error(self):
        log_msg = 'abort, retry, error'
        self.mh.emit(self._log_record(logging.ERROR, log_msg))
        level, text = mock_messages[-1]
        self.assertEqual(messages.ERROR, level,
            'ERROR log level converted to django messages ERROR')
        self.assertEqual(log_msg, text,
            'log message stored as django message text')

    def test_emit_critical(self):
        log_msg = 'critical hit!'
        self.mh.emit(self._log_record(logging.CRITICAL, log_msg))
        level, text = mock_messages[-1]
        self.assertEqual(messages.ERROR, level,
            'CRITICAL log level converted to django messages ERROR')
        self.assertEqual(log_msg, text,
            'log message stored as django message text')

    def test_emit_debug(self):
        log_msg = 'if debugging is the process of removing bugs...'
        self.mh.emit(self._log_record(logging.DEBUG, log_msg))
        level, text = mock_messages[-1]
        self.assertEqual(messages.DEBUG, level,
            'DEBUG log level converted to django messages DEBUG')
        self.assertEqual(log_msg, text,
            'log message stored as django message text')
