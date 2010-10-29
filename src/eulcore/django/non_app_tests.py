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
    
def clear_mock_messages():
    while mock_messages:
        mock_messages.pop()

log.messages.add_message = mock_add_message

class DjangoMessageHandlerTest(TestCase):
    # very simple mock add_message function (avoid using django messaging infrastructure for tests)
    
    def _log_record(self, level, text):
        # simple method to generate a logRecord to pass to handler emit function
        return logging.LogRecord('test', level, __name__, 0,
            text, [], [])

    def setUp(self):
        self.mh = log.DjangoMessageHandler('request')

    def tearDown(self):
        clear_mock_messages()

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

try:
    # NullHandler added in python 2.7
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

class MessageLoggingTest(TestCase):

    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(NullHandler())
        self.request = 'rqst'

    def tearDown(self):
        clear_mock_messages()

    def test_basic_functionality(self):
        with log.message_logging(self.request, __name__, logging.DEBUG):
            self.logger.critical('criticize this')
            self.logger.debug('rebug')
            self.logger.info('fyi')

        # after context - this should *not* be converted to a message
        self.logger.error('pick me! pick me!')
        
        self.assertEqual(3, len(mock_messages),
            'There should be 3 log messages (3 in context, 1 outside), got %d' % len(mock_messages))
        self.assertEqual('criticize this', mock_messages[0][1])
        self.assertEqual('rebug', mock_messages[1][1])
        self.assertEqual('fyi', mock_messages[2][1])

    def test_log_level(self):
        
        with log.message_logging(self.request, __name__, logging.ERROR):
            self.logger.error('oops')
            self.logger.debug('niggling details')

        self.assertEqual(1, len(mock_messages),
            'There should be only 1 log messages (level filter), got %d' % \
            len(mock_messages))

    def test_logname(self):
        otherlogger = logging.getLogger('my.other.logger')
        otherlogger.setLevel(logging.DEBUG)
        otherlogger.addHandler(NullHandler())

        with log.message_logging(self.request, 'my.other.logger', logging.DEBUG):
            self.logger.error('main log error')
            otherlogger.error('other log error')

        self.assertEqual(1, len(mock_messages),
            'There should be only 1 log messages (filter by log name), got %d' \
            % len(mock_messages))

