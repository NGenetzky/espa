import json
import time

from mongoengine.django.auth import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import loader
from django.template import RequestContext
from django.views.generic import View
from django.views.generic.edit import FormView

from forms import StatusMessageForm
from ordering.models import Configuration, Order, Product
from ordering.views import AbstractView

class Index(AbstractView):
    template = 'console/index.html'

    def _get_system_status(self, ctx):
        ctx['display_sys_status'] = True
        ctx['submitted_units'] = Product.objects.filter(status='submitted').count()
        ctx['onorder_units'] = Product.objects.filter(status='onorder').count()
        ctx['oncache_units'] = Product.objects.filter(status='oncache').count()
        ctx['queued_units'] = Product.objects.filter(status='queued').count()
        ctx['process_units'] = Product.objects.filter(status='processing').count()
        ctx['error_units'] = Product.objects.filter(status='error').count()

        try:
            ondemand_enabled = Configuration.objects.get(key='ondemand_enabled')
            if ondemand_enabled.value.lower() == 'true':
                ctx['ondemand_enabled'] = True
            else:
                ctx['ondemand_enabled'] = False
        except Configuration.DoesNotExist:
            ctx['ondemand_enabled'] = False

    def get(self, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        if not user.is_staff:
            return HttpResponseRedirect(reverse('login'))

        c = self._get_request_context(request)
        self._get_system_status(c)
        t = loader.get_template(self.template)

        return HttpResponse(t.render(c))

class UpdateOnDemandStatus(View):
    def get(self, request, state_in):
        if not request.user.is_staff:
            response = {'result': 'error', 'message': 'Not authorized to perform this action'}
            return HttpResponse(json.dumps(response), content_type="application/json")
    
        ondemand_enabled, created = Configuration.objects.get_or_create(key="ondemand_enabled")
        if state_in.lower() == 'on':
            ondemand_enabled.value = 'true'
        elif state_in.lower() == 'off':
            ondemand_enabled.value = 'false'
        else:
            response = {'result': 'error', 'message': 'Invalid option. Valid options are: on, off'}
            return HttpResponse(json.dumps(response), content_type="application/json")

        ondemand_enabled.save()

        response = {'result': 'success', 'message': 'success'}
        return HttpResponse(json.dumps(response), content_type="application/json")

class RestartFailedByOrder(View):
    def get(self, request, order_in):
        if not request.user.is_staff:
            response = {'result': 'error', 'message': 'Not authorized to perform this action'}
            return HttpResponse(json.dumps(response), content_type="application/json")

        try: 
            Product.objects(order=order_in, status='error').update(set__status='submitted')
        except Exception, e:
            response = {'result': 'error', 'message': 'Update failed {}'.format(str(e))}
            return HttpResponse(json.dumps(response), content_type="application/json")
            
        response = {'result': 'success', 'message': 'success'}
        return HttpResponse(json.dumps(response), content_type="application/json")

class RestartFailedAll(View):
    def get(self, request):
        if not request.user.is_staff:
            response = {'result': 'error', 'message': 'Not authorized to perform this action'}
            return HttpResponse(json.dumps(response), content_type="application/json")

        try: 
            Product.objects(status='error').update(set__status='submitted')
        except Exception, e:
            response = {'result': 'error', 'message': 'Update failed {}'.format(str(e))}
            return HttpResponse(json.dumps(response), content_type="application/json")
            
        response = {'result': 'success', 'message': 'success'}
        return HttpResponse(json.dumps(response), content_type="application/json")

class ShowOrders(AbstractView):
    template = 'console/show_orders.html'

    def get(self, request, status_in):
        if not request.user.is_staff:
            return HttpResponseRedirect(reverse('login'))

        products = Product.objects.filter(status=status_in)

        t = loader.get_template(self.template)
        c = self._get_request_context(request, {'status_in': status_in, 'scenes': products})

        return HttpResponse(t.render(c))


class StatusMessage(SuccessMessageMixin, AbstractView, FormView):
    template_name = 'console/statusmsg.html'
    form_class = StatusMessageForm
    success_url = 'statusmsg'
    success_message = 'Status message updated'

    def get(self, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        if not user.is_staff:
            return HttpResponseRedirect(reverse('login'))

        return super(StatusMessage, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = User.objects.get(username=request.user.username)
        if not user.is_staff:
            return HttpResponseRedirect(reverse('login'))

        return super(StatusMessage, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(StatusMessage, self).get_context_data(**kwargs)
        self._get_system_status(context)

        try:
            update_date = Configuration.objects.get(key="system_message_updated_date")
            context['update_date'] = update_date.value
        except Configuration.DoesNotExist:
            context['update_date'] = 'n/a'

        try:
            updated_by = Configuration.objects.get(key="system_message_updated_by")
            context['updated_by'] = updated_by.value
        except Configuration.DoesNotExist:
            context['updated_by'] = 'n/a'

        return context


    def get_initial(self):
        return_data = {}
        try:
            title = Configuration.objects.get(key="system_message_title")
            return_data['title'] = title.value
        except Configuration.DoesNotExist:
            return_data['title'] = ''

        try:
            message = Configuration.objects.get(key="system_message_body")
            return_data['message'] = message.value
        except Configuration.DoesNotExist:
            return_data['message'] = ''

        try:
            display = Configuration.objects.get(key="display_system_message")
            if display.value.lower() == 'true':
                return_data['display'] = True
            else:
                return_data['display'] = False
        except Configuration.DoesNotExist:
            return_data['display'] = False

        return return_data

    def form_valid(self, form):
        title, created = Configuration.objects.get_or_create(key="system_message_title")
        title.value = form.cleaned_data['title']
        title.save()

        message, created = Configuration.objects.get_or_create(key="system_message_body")
        message.value = form.cleaned_data['message']
        message.save()

        display, created = Configuration.objects.get_or_create(key="display_system_message")
        if form.cleaned_data['display']:
            display.value = 'true'
        else:
            display.value = 'false'
        display.save()

        date_updated, created = Configuration.objects.get_or_create(key="system_message_updated_date")
        date_updated.value = time.strftime('%a %b %d %Y %X')
        date_updated.save()

        username, created = Configuration.objects.get_or_create(key="system_message_updated_by")
        username.value = self.request.user.username
        username.save()
        
        return super(StatusMessage, self).form_valid(form)

class DisplayOrder(AbstractView):
    template_name = 'console/displayorder.html'

    def get(self, request, orderid_in):
        user = User.objects.get(username=request.user.username)
        if not user.is_staff:
            return HttpResponseRedirect(reverse('login'))

        order = Order.objects.get(id=orderid_in)
        products = Product.objects.filter(order=orderid_in)

        t = loader.get_template(self.template_name)
        c = self._get_request_context(request, {'order': order, 'scenes': products})

        return HttpResponse(t.render(c))
