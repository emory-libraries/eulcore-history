# file django/taskresult/models.py
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

from datetime import datetime
from celery.result import AsyncResult
from celery.signals import task_prerun, task_postrun

from django.contrib import admin
from django.db import models

# store details about pdf reload celery task results for display on admin page
class TaskResult(models.Model):
    label = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    url = models.URLField()
    created = models.DateTimeField(default=datetime.now)
    task_id = models.CharField(max_length=100)
    task_start = models.DateTimeField(blank=True, null=True)
    task_end = models.DateTimeField(blank=True, null=True)

    @property
    def task(self):
        return AsyncResult(self.task_id)

    def __unicode__(self):
        return self.label

    @property
    def duration(self):
        if self.task_end and self.task_start:
            return self.task_end - self.task_start
        else:
            return ''

# listeners to celery signals to store start and end time for tasks
# NOTE: these functions do not filter on the sender/task function

def taskresult_start(sender, task_id, **kwargs):
    try:
        tr = TaskResult.objects.get(task_id=task_id)
        tr.task_start = datetime.now()
        tr.save()
    except Exception:
        pass
task_prerun.connect(taskresult_start)

def taskresult_end(sender, task_id, **kwargs):
    try:
        tr = TaskResult.objects.get(task_id=task_id)
        tr.task_end = datetime.now()
        tr.save()
    except Exception:
        pass
task_postrun.connect(taskresult_end)

class TaskResultAdmin(admin.ModelAdmin):
    list_display = ('object_id', 'label', 'created', 'task_start', 'task_end', 'duration')
    list_filter  = ('created',)
    # disallow creating task results via admin site
    def has_add_permission(self, request):
        return False

admin.site.register(TaskResult, TaskResultAdmin)



