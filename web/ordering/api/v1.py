import json
import collections
from espa_common import sensor

import django.contrib.auth

from espa_common import utilities

from ordering import api

from ordering import validators
from ordering import models

from django.conf import settings

from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.db.models import Q

from django.http import Http404

from django.views.generic import View
from django.contrib.auth.models import User

#
#class AjaxForm(View):
#    def get(self, request):
#        template = 'ordering/test.html'
#        c = self._get_request_context(request)
#        t = loader.get_template(template)
#        return HttpResponse(t.render(c))


#class TestAjax(View):
#
#    def get(self, request):
#
#        name = request.GET.get('name', '')
#
#        data = {'user': request.user.get_username(),
#                'name': name,
#                'status': 'GET request ok'}
#
#        return api.json_response(data)

#    def post(self, request):
#
#        name = "No name provided"
#        if 'name' in request.POST:
#            name = request.POST['name']
#
#        age = "No age provided"
#        if 'age' in request.POST:
#            age = request.POST['age']

#        data = {'user': request.user.get_username(),
#                'name': name,
#                'age': age,
#                'status': 'POST request ok'}
#
#        return api.json_response(data)


class Description(View):
    pass

class Limits(View):
    pass

class Order(View):
    
    input_product_list = None

    def _get_order_description(self, parameters):
        description = None
        if 'order_description' in parameters:
            description = parameters['order_description']
        return description

    def _get_order_options(self, request):

        defaults = models.Order.get_default_options()

        # This will make sure no additional options past the ones we are
        # expecting will make it into the database
        #for key in request.POST.iterkeys():
        for key in defaults:
            if key in request.POST.iterkeys():
                val = request.POST[key]
                if val is True or str(val).lower() == 'on':
                    defaults[key] = True
                elif utilities.is_number(val):
                    if str(val).find('.') != -1:
                        defaults[key] = float(val)
                    else:
                        defaults[key] = int(val)
                else:
                    defaults[key] = val

        return defaults

    def _get_input_product_list(self, request):

        if not self.input_product_list:
            if 'input_product_list' in request.FILES:
                _ipl = request.FILES['input_product_list'].read().split('\n')
                self.input_product_list = _ipl

        retval = collections.namedtuple("InputProductListResult",
                                        ['input_products', 'not_implemented'])
        retval.input_products = list()
        retval.not_implemented = list()

        if self.input_product_list:
            for line in self.input_product_list:

                line = line.strip()

                try:
                    s = sensor.instance(line)
                    retval.input_products.append(s)
                except sensor.ProductNotImplemented, ni:
                    retval.not_implemented.append(ni.product_id)

        return retval

    def _get_verified_input_product_list(self, request):

        ipl = self._get_input_product_list(request)

        if ipl:
            payload = {'input_products': ipl.input_products}

            lplv = validators.LandsatProductListValidator(payload)

            mplv = validators.ModisProductListValidator(payload)

            landsat = lplv.get_verified_input_product_set(ipl.input_products)

            modis = mplv.get_verified_input_product_set(ipl.input_products)

            return list(landsat.union(modis))
        else:
            return None

    def get(self, request, orderid):
        '''Request handler to get the full listing of all the scenes
        & statuses for an order

        Keyword args:
        request -- HTTP request object
        orderid -- the order id for the order

        Return:
        HttpResponse
        '''

        try:
            c = dict()
            c['order'], c['scenes'] = models.Order.get_order_details(orderid)
            return api.json_response(c)
        except models.Order.DoesNotExist:
            raise Http404

    def post(self, request):
        '''Request handler for new order submission

        Keyword args:
        request -- HTTP request object

        Return:
        HttpResponseRedirect upon successful submission
        HttpResponse if there are errors in the submission
        '''
        #request must be a POST and must also be encoded as multipart/form-data
        #in order for the files to be uploaded

        validator_parameters = {}

        # coerce the request.POST to be a normal Python dictionary
        validator_parameters = dict(request.POST)

        # retrieve the namedtuple for the input product list
        ipl = self._get_input_product_list(request)

        # send the validator only the items in the list that could actually
        # be instantiated as a sensor.  The other tuple item not_implemented
        # is being ignored unless we want to tell the users about all the
        # junk they included in their input file
        validator_parameters['input_products'] = ipl.input_products

        validator = validators.NewOrderValidator(validator_parameters)

        validation_errors = validator.errors()

        #if validator.errors():
        if validation_errors:

            c = self._get_request_context(request)

            #unwind the validator errors.  It comes out as a dict with a key
            #for the input field name and a value of a list of error messages.
            # At this point we are only displaying the error messages in one
            # block but going forward will be able to put the error message
            # right next to the field where the error occurred once the
            # template is properly modified.
            errors = validation_errors.values()

            error_list = list()

            for e in errors:
                for m in e:
                    m = m.replace("\n", "<br/>")
                    m = m.replace("\t", "    &#149; ")
                    m = m.replace(" ", "&nbsp;")
                    error_list.append(m)

            c['errors'] = sorted(error_list)
            c['user'] = request.user
            
            return api.json_response(c)
            
        else:

            vipl = self._get_verified_input_product_list(request)

            order_options = self._get_order_options(request)

            order_type = "level2_ondemand"

            if order_options['include_statistics'] is True:
                vipl.append("plot")
                order_type = "lpcs"

            option_string = json.dumps(order_options,
                                       sort_keys=True,
                                       indent=4)

            desc = self._get_order_description(request.POST)

            order = models.Order.enter_new_order(request.user.username,
                                                 'espa',
                                                 vipl,
                                                 option_string,
                                                 order_type,
                                                 note=desc
                                                )
                                                
            response = {'status':order.status,
                        'orderid':order.orderid,
                        'status_url':reverse('api_v1_order_details',
                                             kwargs={'orderid': order.orderid})
                       }

            return api.json_response(response)


class Orders(View):
        
    def get(self, request, email=None):
        '''Request handler for displaying all user orders

        Keyword args:
        request -- HTTP request object
        email -- the user's email
        
        Return:
        HttpResponse
        '''
       
        try:
            if email is None or not utilities.validate_email(email):
                user = User.objects.get(username=request.user.username)
                email = user.email

            orders = models.Order.list_all_orders(email)
            
        except models.Order.DoesNotExist:
            raise Http404
    
        return api.json_response({'email': email, 'orders': orders})
