from django.shortcuts import render_to_response
from django.template import RequestContext

from eulcore.django.taskresult.models import TaskResult

def recent_tasks(request):
    # get the 25 most recent task results to display status
    recent_tasks = TaskResult.objects.order_by('-created')[:25]
    return render_to_response('taskresult/recent.html', {
                'task_results': recent_tasks,
                }, context_instance=RequestContext(request))

