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

# local objects and methods
from espa_exception import ErrorCodes, ESPAException
from transfer import transfer_file


espa_base_working_dir_envvar = 'ESPA_WORK_DIR'


#=============================================================================
def create_directory (directory):
    '''
    Description:
        Create the specified directory with some error checking.
    '''

    # Create/Make sure the directory exists
    try:
        os.makedirs (directory, mode=0755)
    except OSError as ose:
        if ose.errno == errno.EEXIST and os.path.isdir (directory):
            pass
        else:
            raise
# END - create_directory


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


#=============================================================================
def initialize_processing_directory (orderid, scene):
    '''
    Description:
        Create the procesing directory for a scene along with it's
        sub-directories.  If the environment variable is not set use the
        current working directory as the base starting point.
    '''

    order_directory = ''

    if not os.environ.has_key (espa_base_working_dir_envvar):
        log ("Warning: Environment variable $%s is not defined" %
            espa_working_dir_var)
    else:
        order_directory = os.environ.get (espa_base_working_dir_envvar)

    # If the directory is '.' or empty, use the current working directory
    if order_directory == '' or order_directory == '.':
        order_directory = os.getcwd()

    # Specify a random directory using orderid
    order_directory += '/' + str(orderid)

    # Just incase remove it, and we don't care about errors
    shutil.rmtree (order_directory, ignore_errors=True)

    # Specify the scene sub-directory
    scene_directory = order_directory + '/' + scene

    # Specify the sub-directories of a processing directory
    stage_directory = scene_directory + '/stage'
    work_directory = scene_directory + '/work'
    output_directory = scene_directory + '/output'

    # Create each of the leaf sub-directories
    try:
        create_directory (stage_directory)
    except Exception, e:
        raise ESPAException (ErrorCodes.creating_stage_dir, str(e)), \
            None, sys.exc_info()[2]

    try:
        create_directory (work_directory)
    except Exception, e:
        raise ESPAException (ErrorCodes.creating_work_dir, str(e)), \
            None, sys.exc_info()[2]

    try:
        create_directory (output_directory)
    except Exception, e:
        raise ESPAException (ErrorCodes.creating_output_dir, str(e)), \
            None, sys.exc_info()[2]

    return (scene_directory, stage_directory, work_directory, output_directory)
# END - initialize_processing_directory


#=============================================================================
def stage_landsat_data (scene, source_host, source_directory, \
  destination_host, destination_directory,
  source_username, source_pw):
    '''
    Description:
      Stages landsat input data and places it on the localhost in the
      specified destination directory
    '''

    filename = '%s.tar.gz' % scene

    source_file = '%s/%s' % (source_directory, filename)
    destination_file = '%s/%s' % (destination_directory, filename)

    try:
        transfer_file (source_host, source_file,
            destination_host, destination_file,
            source_username=source_username, source_pw=source_pw)
    except Exception, e:
        raise ESPAException (ErrorCodes.staging_data, str(e)), \
            None, sys.exc_info()[2]

    return destination_file
# END - stage_landsat_data

