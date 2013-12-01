from django.conf.urls import patterns, include, url

from budget import views

urlpatterns = patterns('',
    url(r'^/?$', views.budget, name='index'),
    url(r'^(?P<year>\d{4})/(?P<month>\d{1,2})/?$', views.budget),
    url(r'^accounts/?$', views.accounts),
    url(r'^accounts/add/?$', views.add_account),
    url(r'^accounts/delete_transaction/(?P<id>\d+)/?$', views.delete_transaction),
    url(r'^accounts/clear_transaction/(?P<id>\d+)/?$', views.clear_transaction),
    url(r'^accounts/add_transaction/?$', views.add_transaction),
    url(r'^accounts/add_tranfer/?$', views.add_transfer),
    url(r'^accounts/(?P<id>\d+)/?$', views.account),
    url(r'^accounts/(?P<id>\d+)/delete/?$', views.delete_account),
    url(r'^accounts/(?P<account_id>\d+)/add_transaction/?$', views.add_transaction),
    url(r'^accounts/(?P<account_id>\d+)/add_tranfer/?$', views.add_transfer),
    url(r'^api/auth/', include('rest_framework.urls', 
        namespace='rest_framework')),
    url(r'^login', 'django.contrib.auth.views.login', 
        {'template_name': 'budget/login.html'}),
    url(r'^logout', 'django.contrib.auth.views.logout',
        {'next_page': 'index'}),
    url(r'^register', views.register),
)
