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

# espa-common objects and methods
from espa_constants import *
from espa_logging import log


#=============================================================================
def transfer_data (source_host, source_file,
                   destination_host, destination_directory):
    '''
    Description:
        Using cp/SCP transfer a file from a source location to a destination
        location.
    '''

    # If both source and destination are localhost we can just copy the data
    cmd = []
    if source_host == 'localhost' and destination_host == 'localhost':
        cmd = ['cp']
    elif source_host == destination_host:
        cmd = ['ssh', source_host, 'cp', source_file, destination_directory]
    else:
        cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-c', 'arcfour', '-C']

    # Build the source portion of the command
    if source_host == 'localhost':
        cmd += [source_file]
    elif source_host != destination_host:
        # Build the SCP command line
        cmd += ['%s:%s' % (source_host, source_file)]

    # Build the destination portion of the command
    if destination_host == 'localhost':
        cmd += [destination_directory]
    elif source_host != destination_host:
        cmd += ['%s:%s' % (destination_host, destination_directory)]

    log ("Transfering [%s:%s] to [%s:%s]" % \
        (source_host, source_file, destination_host, destination_directory))

    # Transfer the data and raise any errors
    output = ''
    try:
        output = subprocess.check_output (cmd)
    except subprocess.CalledProcessError, e:
        log (output)
        log ("Error: Failed to transfer data")
        raise e
# END - transfer_data


#=============================================================================
def stage_landsat_data (scene, source_host, source_directory, \
  destination_host, destination_directory):
    '''
    Description:
      Stages landsat input data and places it on the localhost in the
      specified destination directory
    '''

    filename = '%s.tar.gz' % scene

    source_filename = '%s/%s' % (source_directory, filename)
    destination_filename = '%s/%s' % (destination_directory, filename)

    transfer_data (source_host, source_filename, destination_host,
        destination_directory)

    return destination_filename
#END - stage_landsat_data

