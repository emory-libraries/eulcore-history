# file django/log.py
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

from contextlib import contextmanager
import logging

from django.contrib import messages

class DjangoMessageHandler(logging.Handler):
    '''A log handler that converts standard python log messages into Django
    messages using the `Django messages framework
    <http://docs.djangoproject.com/en/dev/ref/contrib/messages/>`_.

    Can only be used in a context that has access to a
    :class:`django.http.HttpRequest` object (normally a view method), since a
    request is required for creating messages.  Recommended to use with
    :meth:`message_logging` context manager.
    '''

    # map python log levels to django message levels
    # - python and django numeric values are currently equivalent,
    #   but it is unclear if that is reliable
    message_level = {
        logging.DEBUG: messages.DEBUG,
        logging.INFO: messages.INFO,
        logging.WARNING: messages.WARNING,
        logging.ERROR: messages.ERROR,
        logging.CRITICAL: messages.ERROR,   # django messages has no critical
        # standard python logging has no equivalent to messages.success
    }

    def __init__(self, request):
        self.request = request
        logging.Handler.__init__(self)

    def emit(self, record):
        # convert into LogRecord into a django message based on level
        if record.levelno in self.message_level:
            messages.add_message(self.request, self.message_level[record.levelno],
                                 self.format(record))


@contextmanager
def message_logging(request, loggername='', level=None):
    '''Context manager to simplify the logging set-up required to use
    :class:`DjangoMessageHandler` as a log handler.

    :param request: :class:`django.http.HttpRequest` object to use for
        adding messages
    :param loggername: logger name to be passed to :meth:`logger.getLogger`
    :param level: log level for messages to be displayed
    
    Example usage::

        def view(request):
            with message_logging(request, 'my.module', logging.INFO):
                # do stuff (i.e., call methods that add logging messages)

    '''
    # initialize message handler, add it the logger, and configure logger
    mh = DjangoMessageHandler(request)
    if level is not None:
        mh.setLevel(level)
    # create a simple formatter and add it to the handler
    formatter = logging.Formatter("%(message)s")
    mh.setFormatter(formatter)
    logger = logging.getLogger(loggername)
    logger.addHandler(mh)

    # if the requested logger is set at a log-level higher than the requested level,
    # temporarily change it
    original_log_level = None
    if level is not None and logger.getEffectiveLevel() > level:
        original_log_level = logger.getEffectiveLevel()
        logger.setLevel(level)

    # do stuff
    yield

    # remove the custom handler
    logger.removeHandler(mh)
    mh.close()

    # restore original log level if it was changed
    if original_log_level is not None:
        logger.setLevel(original_log_level)

