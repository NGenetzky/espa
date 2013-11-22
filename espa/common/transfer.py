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
    else:
        cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-c', 'arcfour', '-C']

    # Build the source portion of the command
    if source_host == 'localhost':
        cmd += [source_file]
    else:
        # Build the SCP command line
        cmd += ['%s:%s' % (source_host, source_file)]

    # Build the destination portion of the command
    if destination_host == 'localhost':
        cmd += [destination_directory]
    else:
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
        log (str(e))
        raise
# END - transfer_data


#=============================================================================
def retrieve_landsat_l1t_scene(options, filename, stage_directory):
    transfer_data (options['source_host'], \
        "%s/%s" % (options['source_directory'], filename), \
        'localhost', stage_directory)
#END - retrieve_landsat_l1t_scene


#=============================================================================
def retrieve_modis_data(options, stage_directory):
    raise Exception ("Error: Not implemented")
#END - retrieve_modis_data


#=============================================================================
if __name__ == '__main__':
    '''
    Description:
        For testing purposes only.
    '''

    try:
        transfer_data('localhost', 'xxxxxx', 'localhost', 'yyyyyy')
    except Exception, e:
        log ("Error: Unable to transfer data")
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

