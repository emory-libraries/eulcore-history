# file django/taskresult/tests.py
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


from time import sleep
from celery.signals import task_prerun, task_postrun
from django.core.urlresolvers import reverse
from django.test import Client, TestCase

from eullocal.django.taskresult.models import TaskResult

class TaskResultTestCase(TestCase):

    def test_start_end_duration(self):
        # create a task and send pre/post run signals to test signal handlers
        id = 'foo'
        tr = TaskResult(label='test task', object_id='id', url='/foo', task_id=id)
        tr.save()
        task_time = 2
        task_prerun.send(sender=TaskResultTestCase, task_id=id)
        sleep(task_time)
        task_postrun.send(sender=TaskResultTestCase, task_id=id)

        tr = TaskResult.objects.get(task_id=id)
        self.assertTrue(tr.task_start,
            'task start time should be set based on celery task_prerun signal')
        self.assertTrue(tr.task_end,
            'task end time should be set based on celery task_postrun signal')
        self.assertEqual(task_time, tr.duration.seconds)


    def test_view_recent(self):
        client = Client()
        # no tasks to display
        response = client.get(reverse('tasks:recent'))
        self.assertContains(response, 'No recent tasks')

        # create some tasks
        task1 = TaskResult(label='test1', object_id='a', url='/foo-a', task_id=id)
        task1.save()
        task2 = TaskResult(label='test2', object_id='b', url='/foo-b', task_id=id)
        task2.save()
        response = client.get(reverse('tasks:recent'))
        self.assertContains(response, task1.label)
        self.assertContains(response, task2.label)
        self.assertContains(response, 'href="%s"' % task1.url)
        self.assertContains(response, 'href="%s"' % task2.url)
        self.assertContains(response, 'PENDING',        # no actual task, shows as pending
            msg_prefix='task status should be displayed in list')
        self.assertEqual(response.context['task_results'][0], task2,
            'newest task should be listed first')
        
