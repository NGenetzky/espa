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


#=============================================================================
def unpack_data (source_file, destination_directory):
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
        log (str(e))
        raise
# END - unpack_data


#=============================================================================
if __name__ == '__main__':
    '''
    Description:
        For testing purposes only.
    '''

    try:
        unpack_data('xxxxxx', 'yyyyyy')
    except Exception, e:
        log ("Error: Unable to unpack data")
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

