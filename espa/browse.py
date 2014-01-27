#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Create a browse image from the surface reflectance product.
  All operations assume everything is in the current directory.

History:
  Original Development (cdr_ecv.py) by David V. Hill, USGS/EROS
  Created Jan/2014 by Ron Dilley, USGS/EROS
    - Gutted the original implementation from cdr_ecv.py and placed it in this
      file.
'''

import os
import sys
import glob

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, debug

# local objects and methods
import util

# Default values
default_resolution = 50


# TODO - At some point in the future we should allow browse generation from
#        L1T, and TOA as well.  Should also consider support for applying
#        color ramps against indices.
#=============================================================================
def do_sr_browse (sr_filename, scene, resolution=default_resolution):
    '''
    Descrription:
      Creates a browse image from the surface relfectance file
    '''
    
    log ("Creating browse product")
                    
    browse_filename = "%s-sr-browse.tif" % scene

    #-------------------------------------------------------------------------
    # Convert to GeoTIFF
    cmd = ['gdal_translate',
           '-a_nodata', '-9999',
           '-a_nodata', '12000',
           '-of', 'GTiff',
           '-sds', sr_filename, 'out.tiff']
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    #-------------------------------------------------------------------------
    # Scale each browse band to 8bit data range
    base_translate_cmd = ['gdal_translate',
                          '-ot', 'Byte',
                          '-scale', '0', '10000', '0', '255',
                          '-of', 'GTIFF']
    cmd = base_translate_cmd + ['out.tiff5', 'browse.tiff5']
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    cmd = base_translate_cmd + ['out.tiff4', 'browse.tiff4']
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    cmd = base_translate_cmd + ['out.tiff3', 'browse.tiff3']
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    #-------------------------------------------------------------------------
    # Create the 3 band composite
    cmd = ['gdal_merge_simple',
           '-in', 'browse.tiff5',
           '-in', 'browse.tiff4',
           '-in', 'browse.tiff3',
           '-out', 'final.tif']
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    #-------------------------------------------------------------------------
    # Project to geographic
    cmd = ['gdalwarp',
           '-dstalpha',
           '-srcnodata', '0',
           '-t_srs', 'EPSG:4326',
           'final.tif', 'warped.tif']
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    #-------------------------------------------------------------------------
    # Resize and rename
    cmd = ['gdal_translate',
           '-co', 'COMPRESS=DEFLATE',
           '-co', 'PREDICTOR=2',
           '-outsize', str(resolution), str(resolution),
           '-a_nodata', '-9999',
           '-of', 'GTIFF',
           'warped.tif', browse_filename]
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    #-------------------------------------------------------------------------
    # Cleanup
    remove_files = ['warped.tif', 'final.tif']
    remove_files += glob.glob('*tiff*')
    cmd = ['rm', '-rf'] + remove_files
    cmd = ' '.join(cmd)
    log ('Running: ' + cmd)
    output = util.execut_cmd (cmd)
    log (output)

    log ("Browse product generation complete...")
# END - do_sr_browse

