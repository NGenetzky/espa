#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description: TODO TODO TODO

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import errno
import sys
import uuid
import shutil
import subprocess
import glob

# espa-common objects and methods
from espa_constants import *
from espa_logging import log


# This contains the valid sensors which are supported
valid_landsat_sensors = ['LT', 'LE']
valid_modis_sensors = ['MODIS']
valid_unpack_sensors = valid_landsat_sensors + valid_modis_sensors


#=============================================================================
def untar_data (source_file, destination_directory):
    '''
    Description:
        Using tar extract the file contents into a destination directory.
    '''

    # If both source and destination are localhost we can just copy the data
    cmd = ['tar', '--directory', destination_directory, '-xvf', source_file]

    log ("Unpacking [%s] to [%s]" % (source_file, destination_directory))

    # Unpack the data and raise any errors
    output = ''
    try:
        output = subprocess.check_output (cmd)
    except subprocess.CalledProcessError, e:
        log (output)
        log ("Error: Failed to unpack data")
        raise
# END - untar_data


#=============================================================================
def unpack_data (data_sensor, source_file, destination_directory):
    '''
    Description:
        Unpacks the data using the appropriate mechanism for the data sensor.
    '''

    if data_sensor not in valid_unpack_sensors:
        raise NotImplementedError ("Unsupported data sensor %s" % data_sensor)

    if data_sensor in valid_landsat_sensors:
        untar_data(source_file, destination_directory)

    elif data_sensor in valid_modis_sensors:
        raise NotImplementedError ("Data sensor %s is not implemented" % \
            data_sensor)
# END - unpack_data

