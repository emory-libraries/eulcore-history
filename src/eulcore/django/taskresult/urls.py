from django.conf.urls.defaults import *

urlpatterns = patterns('eulcore.django.taskresult.views',
    url(r'^recent/$', 'recent_tasks', name='recent'),
)
