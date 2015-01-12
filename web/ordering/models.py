import datetime
import json

from mongoengine.django.auth import User
from mongoengine import *

from espa_common import sensor

class UserProfile (Document):
    '''Extends the information attached to ESPA users with a one-to-one
    relationship. The other options were to extend the actual Django User
    model or create an entirely new User model.  This is the cleanest and
    recommended method per the Django docs.
    '''
    # reference to the User this Profile belongs to
    user = ReferenceField(User)

    # The EE contactid of this user
    contactid = StringField(max_length=10)


class Order(Document):
    '''Persistent object that models a user order for processing.'''

    def __unicode__(self):
        return self.id

    ORDER_TYPES = (
        ('level2_ondemand', 'Level 2 On Demand'),
        ('lpcs', 'Product Characterization')
    )

    STATUS = (
        ('ordered', 'Ordered'),
        ('partial', 'Partially Filled'),
        ('complete', 'Complete')
    )

    ORDER_SOURCE = (
        ('espa', 'ESPA'),
        ('ee', 'EE')
    )

    ORDER_PRIORITY = (
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High')
    )

    # orderid should be in the format email_MMDDYY_HHMMSS
    id = StringField(max_length=255, primary_key=True)

    # reference the user that placed this order
    user = ReferenceField(User)

    # order_type describes the order characteristics so we can use logic to
    # handle multiple varieties of orders
    order_type = StringField(max_length=50,
                             choices=ORDER_TYPES)

    priority = StringField(max_length=10,
                           choices=ORDER_PRIORITY)

    # date the order was placed
    order_date = DateTimeField()

    # date the order completed (all scenes completed or marked unavailable)
    completion_date = StringField()

    initial_email_sent = DateTimeField()

    completion_email_sent = DateTimeField()

    #o ne of order.STATUS
    status = StringField(max_length=20, choices=STATUS)

    # space for users to add notes to orders
    note = StringField(max_length=2048)

    # json for all product options
    product_options = DictField()

    # one of Order.ORDER_SOURCE
    order_source = StringField(max_length=10,
                               choices=ORDER_SOURCE)

    # populated when the order is placed through EE vs ESPA
    ee_order_id = StringField(max_length=13)

    @staticmethod
    def get_default_product_options():
        '''Factory method to return default product selection options

        Return:
        Dictionary populated with default product options
        '''
        o = {}
        # standard product selection options
        o['include_source_data'] = False            # underlying raster
        o['include_source_metadata'] = False        # source metadata
        o['include_customized_source_data'] = False
        o['include_sr_toa'] = False           # LEDAPS top of atmosphere
        o['include_sr_thermal'] = False       # LEDAPS band 6
        o['include_sr'] = False               # LEDAPS surface reflectance
        o['include_sr_browse'] = False        # surface reflectance browse
        o['include_sr_ndvi'] = False          # normalized difference veg
        o['include_sr_ndmi'] = False          # normalized difference moisture
        o['include_sr_nbr'] = False           # normalized burn ratio
        o['include_sr_nbr2'] = False          # normalized burn ratio 2
        o['include_sr_savi'] = False          # soil adjusted vegetation
        o['include_sr_msavi'] = False         # modified soil adjusted veg
        o['include_sr_evi'] = False           # enhanced vegetation
        o['include_solr_index'] = False       # solr search index record
        o['include_cfmask'] = False           # (deprecated)
        o['include_statistics'] = False       # should we do stats & plots?

        return o

    @staticmethod
    def get_default_projection_options():
        '''Factory method to return default reprojection options

        Return:
        Dictionary populated with default reprojection options
        '''
        o = {}
        o['reproject'] = False             # reproject all rasters (True/False)
        o['target_projection'] = None      # if 'reproject' which projection?
        o['central_meridian'] = None       #
        o['false_easting'] = None          #
        o['false_northing'] = None         #
        o['origin_lat'] = None             #
        o['std_parallel_1'] = None         #
        o['std_parallel_2'] = None         #
        o['datum'] = 'wgs84'
        o['longitude_pole'] = None         #
        o['latitude_true_scale'] = None

        #utm only options
        o['utm_zone'] = None               # 1 to 60
        o['utm_north_south'] = None        # north or south

        return o

    @staticmethod
    def get_default_subset_options():
        '''Factory method to return default subsetting/framing options

        Return:
        Dictionary populated with default subsettings/framing options
        '''
        o = {}
        o['image_extents'] = False       # modify image extent(subset or frame)
        o['image_extents_units'] = None  # what units are the coords in?
        o['minx'] = None                 #
        o['miny'] = None                 #
        o['maxx'] = None                 #
        o['maxy'] = None                 #
        return o

    @staticmethod
    def get_default_resize_options():
        '''Factory method to return default resizing options

        Return:
        Dictionary populated with default resizing options
        '''
        o = {}
        #Pixel resizing options
        o['resize'] = False            # resize output pixel size (True/False)
        o['pixel_size'] = None         # if resize, how big (30 to 1000 meters)
        o['pixel_size_units'] = None   # meters or dd.

        return o

    @staticmethod
    def get_default_resample_options():
        '''Factory method to returns default resampling options

        Return:
        Dictionary populated with default resampling options
        '''
        o = {}
        o['resample_method'] = 'near'  # how would user like to resample?

        return o

    @staticmethod
    def get_default_output_format():
        o = {}
        o['output_format'] = 'gtiff'
        return o

    @classmethod
    def get_default_options(cls):
        '''Factory method to return default espa order options

        Return:
        Dictionary populated with default espa ordering options
        '''
        o = {}
        o.update(cls.get_default_product_options())
        o.update(cls.get_default_projection_options())
        o.update(cls.get_default_subset_options())
        o.update(cls.get_default_resize_options())
        o.update(cls.get_default_resample_options())
        o.update(cls.get_default_output_format())

        return o

    @staticmethod
    def get_default_ee_options():
        '''Factory method to return default espa order options for orders
        originating in through Earth Explorer

        Return:
        Dictionary populated with default espa options for ee
        '''
        o = Order.get_default_options()
        o['include_sr'] = True

        return o

    @staticmethod
    def generate_order_id(email):
        '''Generate espa order id if the order comes from the bulk ordering
        or the api'''
        d = datetime.datetime.now()
        return '%s-%s%s%s-%s%s%s' % (email,
                                     str(d.month).zfill(2),
                                     str(d.day).zfill(2),
                                     d.year,
                                     str(d.hour).zfill(2),
                                     str(d.minute).zfill(2),
                                     str(d.second).zfill(2))

    @staticmethod
    def generate_ee_order_id(email, eeorder):
        '''Generate an order id if the order came from Earth Explorer

        Keyword args:
        email -- Email address of the requestor
        eeorder -- The Earth Explorer order id

        Return:
        An order id string for the espa system for ee created orders
        str(email-eeorder)
        '''
        return '%s-%s' % (email, eeorder)

    @staticmethod
    def get_order_details(orderid):
        '''Returns the full order and all attached scenes.  This can also
        be handled by just returning the order object, but this is going to
        be used primarily in a template so its simpler to return both sets
        of objects on their own.

        Keyword args:
        orderid -- the orderid as held in the Order table

        Return:
        A tuple of orders, scenes
        '''
        order = Order.objects.get(id=orderid)
        products = Product.objects.filter(order=order.id)
        return order, products

    @staticmethod
    def list_all_orders(email):
        '''lists out all orders for a given user

        Keyword args:
        email -- The email address of the user

        Return:
        A queryresult of orders for the given email.
        '''
        user_obj = User.objects(email=email).first()
        o = Order.objects.filter(Q(user=user_obj)).order_by('-order_date')

        return o

    @staticmethod
    #@transaction.atomic
    def enter_new_order(username,
                        order_source,
                        scene_list,
                        option_dict,
                        order_type,
                        note=''):
        '''Places a new espa order in the database

        Keyword args:
        username -- Username of user placing this order
        order_source -- Should always be 'espa'
        scene_list -- A list containing scene ids
        option_dict -- Dictionary of options for the order
        note -- Optional user supplied note

        Return:
        The fully populated Order object
        '''

        # find the user
        user = User.objects.get(username=username)

        # determine a simple priority classification (for now)
        order_size = len(scene_list)

        priority = 'normal'

        if order_size <= 100:
            priority = 'high'
        elif order_size > 100 and order_size <= 500:
            priority = 'normal'
        else:
            priority = 'low'

        # create the order
        order = Order()
        order.id = Order.generate_order_id(user.email)
        order.user = user
        order.note = note
        order.status = 'ordered'
        order.order_source = order_source
        order.order_type = order_type
        order.order_date = datetime.datetime.now()
        order.product_options = option_dict
        order.priority = priority
        order.save()

        # save the scenes for the order
        for s in set(scene_list):

            sensor_type = None

            if s == 'plot':
                sensor_type = 'plot'
            elif isinstance(sensor.instance(s), sensor.Landsat):
                sensor_type = 'landsat'
            elif isinstance(sensor.instance(s), sensor.Modis):
                sensor_type = 'modis'

            product = Product()
            product.name = s
            product.order = order
            product.order_date = datetime.datetime.now()
            product.status = 'submitted'
            product.sensor_type = sensor_type
            product.save()

        return order


class Product(Document):
    '''Persists a scene object as defined from the ordering and tracking
    perspective'''

    def __unicode__(self):
        return "%s (%s)" % (self.name, self.status)

    #enumeration of valid status flags a scene may have
    STATUS = (
        ('submitted', 'Submitted'),
        ('onorder', 'On Order'),
        ('oncache', 'On Cache'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('complete', 'Complete'),
        ('retry', 'Retry'),
        ('unavailable', 'Unavailable'),
        ('error', 'Error')
    )

    SENSOR_PRODUCT = (
        ('landsat', 'Landsat'),
        ('modis', 'Modis'),
        ('plot', 'Plotting and Statistics')
    )

    #scene file name, with no suffix
    name = StringField(max_length=256)

    #flags product as either landsat, modis or plot
    sensor_type = StringField(max_length=50, choices=SENSOR_PRODUCT)

    #scene system note, used to add message to users
    note = StringField(max_length=2048)

    #Reference to the Order this Product is associated with
    order = ReferenceField(Order)

    #holds the name of the processing job that is producing this product
    job_name = StringField(max_length=255)

    #full path including filename where this scene has been distributed to
    #minus the host and port. signifies that this scene is distributed
    product_distro_location = StringField(max_length=1024)

    #full path for scene download on the distribution node
    product_dload_url = StringField(max_length=1024)

    #full path (with filename) for scene checksum on distribution filesystem
    cksum_distro_location = StringField(max_length=1024)

    #full url this file can be downloaded from
    cksum_download_url = StringField(max_length=1024)

    # This will only be populated if the scene had to be placed on order
    #through EE to satisfy the request.
    tram_order_id = StringField(max_length=13)

    # Flags for order origination.  These will only be populated if the scene
    # request came from EE.
    ee_unit_id = IntField()

    # General status flags for this scene

    #Status.... one of Submitted, Ready For Processing, Processing,
    #Processing Complete, Distributed, or Purged
    status = StringField(max_length=30, choices=STATUS)

    #Where is this scene being processed at?  (which machine)
    processing_location = StringField(max_length=256)

    #Time this scene was finished processing
    completion_date = DateTimeField()

    #Final contents of log file... should be put added when scene is marked
    #complete.
    log_file_contents = StringField()

    #If the status is 'retry', after what date should the retry occur?
    retry_after = DateTimeField()

    #max number of retries before moving to error status
    #default to 5
    retry_limit = IntField(min_value=0, max_value=999, default=5)

    #current number of retries, initialized to 0
    retry_count = IntField(min_value=0, max_value=999, default=0)


class Configuration(Document):
    '''Implements a key/value datastore on top of a relational database
    '''
    key = StringField(max_length=255, unique=True)
    value = StringField(max_length=2048)

    def __unicode__(self):
        return ('%s : %s') % (self.key, self.value)

    def getValue(self, key):
        try:
            value = Configuration.objects.get(key=key).value

            return str(value)
        except:
            return ''


class DownloadSection(Document):
    ''' Persists grouping of download items and controls appearance order'''
    title = StringField('name', max_length=255)
    text = StringField('section_text')
    display_order = IntField()
    visible = BooleanField('visible')


class Download(Document):
    section = ReferenceField(DownloadSection)
    target_name = StringField('target_name', max_length=255)
    target_url = URLField('target_url')
    checksum_name = StringField('checksum_name',
                                     max_length=255)
    checksum_url = URLField('checksum_url')
    readme_text = StringField('readme_text')
    display_order = IntField()
    visible = BooleanField('visible')


class Tag(Document):
    tag = StringField('tag', max_length=255)
    description = StringField('description')
    last_updated = DateTimeField('last_updated')

    def __unicode__(self):
        return self.tag

    def save(self, *args, **kwargs):
        self.last_updated = datetime.datetime.now()
        super(Tag, self).save(*args, **kwargs)


class DataPoint(Document):
    tags = ListField(ReferenceField(Tag))
    key = StringField('key', max_length=250)
    command = StringField('command', max_length=2048)
    description = StringField('description')
    enable = BooleanField('enable')
    last_updated = DateTimeField('last_updated')

    def __unicode__(self):
        return "%s:%s" % (self.key, self.command)

    def save(self, *args, **kwargs):
        self.last_updated = datetime.datetime.now()
        super(DataPoint, self).save(*args, **kwargs)

    @staticmethod
    def get_data_points(tagnames=[]):
        js = {}

        # TODO fix this
        #if len(tagnames) > 0:
        #    dps = DataPoint.objects.filter(enable=True, tags__tag__in=tagnames)
        #else:
        #    dps = DataPoint.objects.filter(enable=True)

        #for d in dps:
        #    js[d.key] = d.command

        return json.dumps(js)
