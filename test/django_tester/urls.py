from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^tasks/', include('eullocal.django.taskresult.urls', namespace='tasks')),
)
