from datetime import datetime
import json
import time
from mongoengine.django.auth import User

from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader
from django.views.generic import View
from django.views.generic.edit import FormView

from forms import StatusMessageForm, OrderForm, ProductForm
from ordering.models import Configuration, Order, Product
from ordering.views import AbstractView

class StaffOnlyMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return redirect('login')
        if not request.user.is_staff:
            raise PermissionDenied
        
        return super(StaffOnlyMixin, self).dispatch(request, *args, **kwargs)


class Index(StaffOnlyMixin, AbstractView):
    template = 'console/index.html'

    def _get_system_status(self, ctx):
        ctx['display_sys_status'] = True
        ctx['submitted_units'] = Product.objects.filter(status='submitted').count()
        ctx['onorder_units'] = Product.objects.filter(status='onorder').count()
        ctx['oncache_units'] = Product.objects.filter(status='oncache').count()
        ctx['queued_units'] = Product.objects.filter(status='queued').count()
        ctx['process_units'] = Product.objects.filter(status='processing').count()
        ctx['error_units'] = Product.objects.filter(status='error').count()
        ctx['retry_units'] = Product.objects.filter(status='retry').count()

        pipeline = [
                    {'$match': {'status': 'complete'}},
                    {'$sort': {'completion_date': -1}},
                    {'$group': {'_id': {'k':'$status'}, 'v': {'$first': '$completion_date'}}}
        ]
        result = Product._get_collection().aggregate(pipeline)
        
        if result['ok'] == 1 and len(result['result']) > 0:
            ctx['last_completed_date'] = result['result'][0]['v']
        else:
            ctx['last_completed_date'] = 'N/A'

        try:
            ondemand_enabled = Configuration.objects.get(key='ondemand_enabled')
            if ondemand_enabled.value.lower() == 'true':
                ctx['ondemand_enabled'] = True
            else:
                ctx['ondemand_enabled'] = False
        except Configuration.DoesNotExist:
            ctx['ondemand_enabled'] = False

    def get(self, request, *args, **kwargs):
        c = self._get_request_context(request, include_system_message=False)
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

class ShowOrders(StaffOnlyMixin, AbstractView):
    template = 'console/show_orders.html'

    def get(self, request, status_in):
        products = Product.objects.filter(status=status_in)

        t = loader.get_template(self.template)
        c = self._get_request_context(request, {'status_in': status_in, 'scenes': products})

        return HttpResponse(t.render(c))


class StatusMessage(StaffOnlyMixin, SuccessMessageMixin, FormView):
    template_name = 'console/statusmsg.html'
    form_class = StatusMessageForm
    success_url = 'statusmsg'
    success_message = 'Status message updated'

    def get(self, request, *args, **kwargs):
        return super(StatusMessage, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return super(StatusMessage, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(StatusMessage, self).get_context_data(**kwargs)

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

class DisplayOrder(StaffOnlyMixin, SuccessMessageMixin, FormView):
    template_name = 'console/displayorder.html'
    form_class = OrderForm
    success_message = 'Order updated'

    def get(self, request, *args, **kwargs):
        return super(DisplayOrder, self).get(request, *args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        return super(DisplayOrder, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('display_order', kwargs={'orderid_in': self.kwargs.get('orderid_in')})
    
    def get_context_data(self, **kwargs):
        context = super(DisplayOrder, self).get_context_data(**kwargs)
        
        context['order'] = Order.objects.get(id=self.kwargs.get('orderid_in'))
        context['products'] = Product.objects.filter(order=self.kwargs.get('orderid_in'))
        return context
        
    def get_initial(self):
        order = Order.objects.get(id=self.kwargs.get('orderid_in'))
        
        initial_data = {}
        initial_data['orderid'] = order.id
        initial_data['user'] = order.user
        initial_data['order_type'] = order.order_type
        initial_data['priority'] = order.priority
        initial_data['order_date'] = order.order_date
        initial_data['complete_date'] = order.completion_date
        initial_data['completion_email_date'] = order.completion_email_sent
        initial_data['status'] = order.status
        initial_data['note'] = order.note
        initial_data['product_options'] = json.dumps(order.product_options, indent=2)
        initial_data['order_source'] = order.order_source
        initial_data['ee_order_id'] = order.ee_order_id
        
        return initial_data
        
    def form_valid(self, form):
        order = Order.objects.get(id=self.kwargs.get('orderid_in'))
        
        order.priority = form.cleaned_data['priority']
        order.status = form.cleaned_data['status']
        order.note = form.cleaned_data['note']
        order.product_options = json.loads(form.cleaned_data['product_options'])
        order.save()
        
        return super(DisplayOrder, self).form_valid(form)

class DisplayProduct(StaffOnlyMixin, SuccessMessageMixin, FormView):
    template_name = 'console/displayproduct.html'
    form_class = ProductForm
    success_message = 'Product updated'

    def get(self, request, *args, **kwargs):
        return super(DisplayProduct, self).get(request, *args, **kwargs)
        
    def post(self, request, *args, **kwargs):
        return super(DisplayProduct, self).post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('display_product', kwargs={'orderid_in': self.kwargs.get('orderid_in'),
                                                  'product_in': self.kwargs.get('product_in')})
    
    def get_context_data(self, **kwargs):
        context = super(DisplayProduct, self).get_context_data(**kwargs)
        
        context['product_name'] = self.kwargs.get('product_in')
        return context
        
    def get_initial(self):
        product = Product.objects.get(name=self.kwargs.get('product_in'), order=self.kwargs.get('orderid_in'))
        
        initial_data = {}
        initial_data['name'] = product.name
        initial_data['sensor_type'] = product.sensor_type
        initial_data['note'] = product.note
        initial_data['job_name'] = product.job_name
        initial_data['product_dist_location'] = product.product_distro_location
        initial_data['product_dl_url'] = product.product_dload_url
        initial_data['cksum_dist_location'] = product.cksum_distro_location
        initial_data['cksum_dl_url'] = product.cksum_download_url
        initial_data['tram_order_id'] = product.tram_order_id
        initial_data['ee_unit_id'] = product.ee_unit_id
        initial_data['status'] = product.status
        initial_data['processing_location'] = product.processing_location
        initial_data['completion_date'] = product.completion_date
        initial_data['log_file_contents'] = product.log_file_contents
        initial_data['retry_after'] = product.retry_after
        initial_data['retry_limit'] = product.retry_limit
        initial_data['retry_count'] = product.retry_count
        
        return initial_data
        
    def form_valid(self, form):
        product = Product.objects.get(name=self.kwargs.get('product_in'), order=self.kwargs.get('orderid_in'))        
        
        product.status = form.cleaned_data['status']
        product.sensor_type = form.cleaned_data['sensor_type']
        product.note = form.cleaned_data['note']
        product.job_name = form.cleaned_data['job_name']
        product.log_file_contents = form.cleaned_data['log_file_contents']
        product.retry_limit = form.cleaned_data['retry_limit']
        
        if form.cleaned_data['retry_after'] == '':
            product.retry_after = None
        else:
            product.retry_after = datetime.strptime(form.cleaned_data['retry_after'], '%Y-%m-%d %H:%M:00+00:00')
        
        product.save()
        
        return super(DisplayProduct, self).form_valid(form)

class ProductsByMachine(StaffOnlyMixin, AbstractView):
    template_name = 'console/productsbymachine.html'
    
    def get(self, request):
        pipeline = [
            {"$match": {"processing_location": {"$exists": 1}}},
            {"$group": {"_id": {"machine": "$processing_location", "status": "$status"}, "count": { "$sum" : 1}}}, 
            {"$project": {"_id": 0, "machine": "$_id.machine", "status": "$_id.status", "count": 1}},
        ]
        results = Product._get_collection().aggregate(pipeline)
        
        machine_info = {}
        for row in results['result']:
            if not row['machine'] in machine_info:
                machine_info[row['machine']] = {}
            machine_info[row['machine']][row['status']] = row['count']                
                
        t = loader.get_template(self.template_name)
        c = self._get_request_context(request, {'machine_info': machine_info})
        
        return HttpResponse(t.render(c))
    

class OrderByUser(AbstractView):
    template_name = 'console/orderbyuser.html'
    
    def get(self, request):
        pipeline = [
                    {'$match': {'status': 'complete'}},
                    {'$sort': {'completion_date': -1}},
                    {'$group': {'_id': {'k':'$status'}, 'v': {'$first': '$completion_date'}}}
        ]
        result = Product._get_collection().aggregate(pipeline)
    
