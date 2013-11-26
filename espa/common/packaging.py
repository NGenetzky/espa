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


# This contains the valid data sources which are supported
valid_unpack_sources = ['landsat', 'modis']


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
def unpack_data (data_source, source_file, destination_directory):
    '''
    Description:
        Unpacks the data using the appropriate mechanism for the data source.
    '''

    if data_source not in valid_unpack_sources:
        raise ValueError("Unsupported data source %s" % data_source)

    metadata = None

    if data_source == 'landsat':
        metadata = untar_data(source_file, destination_directory)

    elif data_source == 'modis':
        raise NotImplementedError("Data source %s is not implemented" % \
            data_source)
# END - unpack_data

