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


from django.shortcuts import render_to_response
from django.template import RequestContext

from eulcore.django.taskresult.models import TaskResult

def recent_tasks(request):
    # get the 25 most recent task results to display status
    recent_tasks = TaskResult.objects.order_by('-created')[:25]
    return render_to_response('taskresult/recent.html', {
                'task_results': recent_tasks,
                }, context_instance=RequestContext(request))

