
from django import forms

from ordering.models import Order, Product

class StatusMessageForm(forms.Form):
    title = forms.CharField(label='Title', required=False, max_length=255)
    
    message = forms.CharField(label='Message',
                              widget=forms.Textarea,
                              required=False)
                              
    display = forms.BooleanField(label='Publish Message', required=False)


class OrderForm(forms.Form):
    readonly_input = {'class': 'readonly-input', 'readonly': False}
    
    orderid = forms.CharField(label='Id', widget=forms.TextInput(attrs=readonly_input))
    user = forms.CharField(label='Username', widget=forms.TextInput(attrs=readonly_input))
    order_type = forms.CharField(label='Order Type', max_length=50, widget=forms.TextInput(attrs=readonly_input))
    priority = forms.ChoiceField(label='Priority', choices=Order.ORDER_PRIORITY)
    order_date = forms.CharField(label='Order Date', required=False, widget=forms.TextInput(attrs=readonly_input))
    complete_date = forms.CharField(label='Completion Date', required=False, widget=forms.TextInput(attrs=readonly_input))
    completion_email_date = forms.CharField(label='Completion Email Sent', required=False, widget=forms.TextInput(attrs=readonly_input))
    status = forms.ChoiceField(label='Order Status', choices=Order.STATUS)
    note = forms.CharField(label='Note', widget=forms.Textarea, required=False)
    product_options = forms.CharField(label='Product Options', widget=forms.Textarea)
    order_source = forms.CharField(label='Order Source', widget=forms.TextInput(attrs=readonly_input))
    ee_order_id = forms.CharField(label='EE Order Id', required=False, widget=forms.TextInput(attrs=readonly_input))
    
    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        
        self.fields['orderid'].widget.attrs['size'] = 40
        self.fields['user'].widget.attrs['size'] = 40
        self.fields['order_type'].widget.attrs['size'] = 40
        self.fields['order_date'].widget.attrs['size'] = 40
        self.fields['complete_date'].widget.attrs['size'] = 40
        self.fields['completion_email_date'].widget.attrs['size'] = 40
        self.fields['order_source'].widget.attrs['size'] = 40
        self.fields['ee_order_id'].widget.attrs['size'] = 40
        

class ProductForm(forms.Form):
    readonly_input = {'class': 'readonly-input', 'readonly': False}
    
    name = forms.CharField(label='Name', widget=forms.TextInput(attrs=readonly_input))
    sensor_type = forms.ChoiceField(label='Sensor Type', choices=Product.SENSOR_PRODUCT)
    note = forms.CharField(label='Note', widget=forms.Textarea, required=False)
    job_name = forms.CharField(label='Job Name', required=False)
    product_dist_location = forms.CharField(label='Product Distro Location', required=False, widget=forms.TextInput(attrs=readonly_input))
    product_dl_url = forms.CharField(label='Product Download URL', required=False, widget=forms.TextInput(attrs=readonly_input))
    cksum_dist_location = forms.CharField(label='Cksum Distro Location', required=False, widget=forms.TextInput(attrs=readonly_input))
    cksum_dl_url = forms.CharField(label='Cksum Download URL', required=False, widget=forms.TextInput(attrs=readonly_input))
    tram_order = forms.CharField(label='TRAM Order Id', required=False, widget=forms.TextInput(attrs=readonly_input))
    ee_unit_id = forms.CharField(label='EE Unit Id', required=False, widget=forms.TextInput(attrs=readonly_input))
    status = forms.ChoiceField(label='Status', choices=Product.STATUS)
    processing_location = forms.CharField(label='Processing Location', required=False, widget=forms.TextInput(attrs=readonly_input))
    completion_date = forms.CharField(label='Completion Date', required=False, widget=forms.TextInput(attrs=readonly_input))
    log_file_contents = forms.CharField(label='Log Contents', widget=forms.Textarea, required=False)
    retry_after = forms.CharField(label='Retry After', required=False)
    retry_limit = forms.CharField(label='Retry Limit')
    retry_count = forms.CharField(label='Retry Count', widget=forms.TextInput(attrs=readonly_input))
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)