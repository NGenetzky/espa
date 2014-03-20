#! /usr/bin/env python

import datetime
from lxml import etree

import espa_metadata

bands_element_path = '{http://espa.cr.usgs.gov/v1.0}bands'

xml = espa_metadata.parse('LT50460282002042EDC01.xml', silence=True)

bands = xml.get_bands()

# Remove the L1T bands by creating a new list of all the others
bands.band[:] = [band for band in bands.band if band.product != 'L1T']

band = espa_metadata.band(product="RDD", name="band1", category="image",
    data_type="UINT8", nlines="7321", nsamps="7951", fill_value="0")

band.set_short_name ("LT5DN")
band.set_long_name ("band 1 digital numbers")
band.set_file_name ("LT50460282002042EDC01_B1.img")

pixel_size = espa_metadata.pixel_size ("30.000000", 30, "meters")
band.set_pixel_size (pixel_size)

band.set_data_units ("digital numbers")

valid_range = espa_metadata.valid_range (min="1", max=255)
band.set_valid_range (valid_range)

toa_reflectance = espa_metadata.toa_reflectance (gain=1.448, bias="-4.28819")
band.set_toa_reflectance (toa_reflectance)

band.set_app_version ("LPGS_12.3.1")

production_date = \
    datetime.datetime.strptime('2014-01-13T06:49:56', '%Y-%m-%dT%H:%M:%S')
band.set_production_date (production_date)

bands.add_band(band)

f = open('exported_1.xml', 'w')
# Create the file and specify the namespace/schema
espa_metadata.export(f, xml, 'xmlns="http://espa.cr.usgs.gov/v1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://espa.cr.usgs.gov/v1.0 http://espa.cr.usgs.gov/static/schema/espa_internal_metadata_v1_0.xsd"')
f.close()

f = open('exported_2.xml', 'w')
xml.export(f, 0, namespacedef_='xmlns="http://espa.cr.usgs.gov/v1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://espa.cr.usgs.gov/v1.0 http://espa.cr.usgs.gov/static/schema/espa_internal_metadata_v1_0.xsd"')
f.close()


# LXML
try:
    f = open ('espa_internal_metadata_v1_0.xsd')
    schema_root = etree.parse (f)
    f.close()
    schema = etree.XMLSchema (schema_root)

    tree = etree.parse ('exported_1.xml')

    schema.assertValid (tree)
except Exception, e:
   print "lxml Validation Error: %s" % e
   print str (e)

