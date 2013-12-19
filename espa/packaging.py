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
def untar_data (source_file, destination_directory):
    '''
    Description:
      Using tar extract the file contents into a destination directory.

    Notes:
      Works with '*.tar.gz' and '*.tar' files.
    '''

    # If both source and destination are localhost we can just copy the data
    cmd = ['tar', '--directory', destination_directory, '-xvf', source_file]

    log ("Unpacking [%s] to [%s]" % (source_file, destination_directory))

    # Unpack the data and raise any errors
    output = ''
    try:
        output = subprocess.check_output (cmd)
    except Exception, e:
        log ("Error: Failed to unpack data")
        raise e
    finally:
        log (output)
# END - untar_data

