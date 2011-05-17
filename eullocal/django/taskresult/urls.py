# file django/taskresult/urls.py
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


from django.conf.urls.defaults import *
from eulcore.django.taskresult.models import TaskResult

def get_recent_tasks():
    # callable to get the latest results at the time when the view is rendered
    # TODO: better way to make this callable? use archive_index instead?
    return TaskResult.objects.order_by('-created')[:25]

urlpatterns = patterns('django.views.generic',
    url(r'^recent/$', 'simple.direct_to_template', {
            'template': 'taskresult/recent.html',
            'extra_context': {
                'task_results': get_recent_tasks,
            },
        }, name='recent'),
    # TODO: use date_based.archive_index generic view here ?
    # no task index page for now, so just redirect to recent 
    url(r'^$', 'simple.redirect_to', {'url': 'recent/'}),
)