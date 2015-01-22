
from django import forms

from ordering.models import Order, Product

class StatusMessageForm(forms.Form):
    title = forms.CharField(label='Title', required=False, max_length=255)
    
    message = forms.CharField(label='Message',
                              widget=forms.Textarea,
                              required=False)
                              
    display = forms.BooleanField(label='Publish Message', required=False)


class OrderForm(forms.Form):    
    orderid = forms.CharField(label='Id')
    user = forms.CharField(label='Username')
    order_type = forms.CharField(label='Order Type', max_length=50)
    priority = forms.ChoiceField(label='Priority', choices=Order.ORDER_PRIORITY)
    order_date = forms.CharField(label='Order Date', required=False)
    complete_date = forms.CharField(label='Completion Date', required=False)
    completion_email_date = forms.CharField(label='Completion Email Sent', required=False)
    status = forms.ChoiceField(label='Order Status', choices=Order.STATUS)
    note = forms.CharField(label='Note', widget=forms.Textarea, required=False)
    product_options = forms.CharField(label='Product Options', widget=forms.Textarea)
    order_source = forms.CharField(label='Order Source')
    ee_order_id = forms.CharField(label='EE Order Id', required=False)
    
    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        
        self.fields['orderid'].widget.attrs['readonly'] = True
        self.fields['user'].widget.attrs['readonly'] = True
        self.fields['order_type'].widget.attrs['readonly'] = True
        self.fields['order_date'].widget.attrs['readonly'] = True
        self.fields['complete_date'].widget.attrs['readonly'] = True
        self.fields['completion_email_date'].widget.attrs['readonly'] = True
        self.fields['order_source'].widget.attrs['readonly'] = True
        self.fields['ee_order_id'].widget.attrs['readonly'] = True
        

class ProductForm(forms.Form):
    name = forms.CharField(label='Name')
    sensor_type = forms.ChoiceField(label='Sensor Type', choices=Product.SENSOR_PRODUCT)
    note = forms.CharField(label='Note', widget=forms.Textarea, required=False)
    job_name = forms.CharField(label='Job Name', required=False)
    product_dist_location = forms.CharField(label='Product Distro Location', required=False)
    product_dl_url = forms.CharField(label='Product Download URL', required=False)
    cksum_dist_location = forms.CharField(label='Cksum Distro Location', required=False)
    cksum_dl_url = forms.CharField(label='Cksum Download URL', required=False)
    tram_order = forms.CharField(label='TRAM Order Id', required=False)
    ee_unit_id = forms.CharField(label='EE Unit Id', required=False)
    status = forms.ChoiceField(label='Status', choices=Product.STATUS)
    processing_location = forms.CharField(label='Processing Location', required=False)
    completion_date = forms.CharField(label='Completion Date', required=False)
    log_file_contents = forms.CharField(label='Log Contents', widget=forms.Textarea, required=False)
    retry_after = forms.CharField(label='Retry After', required=False)
    retry_limit = forms.CharField(label='Retry Limit')
    retry_count = forms.CharField(label='Retry Count')
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        
        self.fields['name'].widget.attrs['readonly'] = True
        self.fields['tram_order'].widget.attrs['readonly'] = True
        self.fields['ee_unit_id'].widget.attrs['readonly'] = True
        self.fields['product_dist_location'].widget.attrs['readonly'] = True
        self.fields['product_dl_url'].widget.attrs['readonly'] = True
        self.fields['cksum_dist_location'].widget.attrs['readonly'] = True
        self.fields['cksum_dl_url'].widget.attrs['readonly'] = True
        self.fields['processing_location'].widget.attrs['readonly'] = True
        self.fields['completion_date'].widget.attrs['readonly'] = True
        self.fields['retry_count'].widget.attrs['readonly'] = True