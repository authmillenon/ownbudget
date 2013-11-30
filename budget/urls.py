from django.conf.urls import patterns, include, url
from django.core.urlresolvers import reverse

from budget import views

urlpatterns = patterns('',
    url(r'^api/auth/', include('rest_framework.urls', namespace='rest_framework')),
)
