from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^tasks/', include('eulcore.django.taskresult.urls', namespace='tasks')),
)