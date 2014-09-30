from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from views import Index, StatusMessage, ShowOrders, UpdateOnDemandStatus

urlpatterns = patterns('', 
    url(r'^statusmsg',
        login_required(StatusMessage.as_view()), name='statusmsg'),
    url(r'^show-orders/(?P<status_in>[A-Za-z]+)/$',
        login_required(ShowOrders.as_view()), name='show_orders'),
    url(r'^update-ondemand/(?P<state_in>[A-Za-z]+)/$',
        login_required(UpdateOnDemandStatus.as_view()), name="update_ondemand"),
    url(r'^$',
        login_required(Index.as_view()), name='consoleindex')
    )
