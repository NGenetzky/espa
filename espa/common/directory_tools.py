#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides a simple mechanism for creating/returning the working directory for
  the specified order and scene.

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import errno
import sys
import shutil

# espa-common objects and methods
from espa_constants import *
from espa_logging import log

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
        create_directory (work_directory)
        create_directory (output_directory)
    except Exception, e:
        raise

    return (scene_directory, stage_directory, work_directory, output_directory)
# END - initialize_processing_directory


#=============================================================================
if __name__ == '__main__':
    '''
    Description:
        For testing purposes only.
    '''

    try:
        directory = initialize_processing_directory ('yyyyyy')
    except Exception, e:
        log ("Error: Unable to create processing directory")
        sys.exit (EXIT_FAILURE)

    print "Created directory %s" % directory

    sys.exit (EXIT_SUCCESS)

