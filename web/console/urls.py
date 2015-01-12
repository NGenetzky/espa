from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from views import Index, StatusMessage, ShowOrders, UpdateOnDemandStatus, DisplayOrder
from views import RestartFailedByOrder, RestartFailedAll, ProductsByMachine

urlpatterns = patterns('', 
    url(r'^statusmsg',
        login_required(StatusMessage.as_view()), name='statusmsg'),
    url(r'^show-orders/(?P<status_in>[A-Za-z]+)/$',
        login_required(ShowOrders.as_view()), name='show_orders'),
    url(r'^update-ondemand/(?P<state_in>[A-Za-z]+)/$',
        login_required(UpdateOnDemandStatus.as_view()), name="update_ondemand"),
    url(r'^display-order/(?P<orderid_in>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}-[0-9]{6,8}-[0-9]{3,6})/$', 
        login_required(DisplayOrder.as_view()), name="display_order"),
    url(r'^restart-failed-by-order/(?P<order_in>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}-[0-9]{6,8}-[0-9]{3,6})/$', 
        login_required(RestartFailedByOrder.as_view()), name='restart_failed_by_order'),
    url(r'^restart-failed-all/$', 
        login_required(RestartFailedAll.as_view()), name='restart_failed_all'),
    url(r'^products-by-machine/$',
        login_required(ProductsByMachine.as_view()), name='products_by_machine'),
    url(r'^$',
        login_required(Index.as_view()), name='consoleindex')
    )
