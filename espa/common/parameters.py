
'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides routines for interfacing with parameters in a dictionary.

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os

# espa-common objects and methods
from espa_constants import *
from espa_logging import log


# This contains the valid sensors and data types which are supported
valid_sensors = ['LT', 'LE'] # TODO TODO TODO - Someday add MODIS
valid_data_types = ['level1', 'sr', 'toa', 'th']


#=============================================================================
def add_standard_parameters (parser):

    parser.add_argument ('--orderid',
        action='store', dest='orderid', required=True,
        help="the order ID associated with this request")

    parser.add_argument ('--scene',
        action='store', dest='scene', required=True,
        help="the scene ID associated with this request")

    parser.add_argument ('--work_directory',
        action='store', dest='work_directory', default=os.curdir,
        help="the scene ID associated with this request")
# END - add_standard_parameters


#=============================================================================
def add_data_type_parameter (parser, choices):
    '''
    Description:
      Adds the data_source parameter to the command line parameters with
      specific choices
    '''

    parser.add_argument ('--data_type',
        action='store', dest='data_type', default='level1',
        choices=choices,
        help="type of the input data")
# END - add_data_source_parameter


#=============================================================================
def add_debug_parameter (parser):
    '''
    Description:
      Adds the debug parameter to the command line parameters
    '''

    parser.add_argument ('--debug',
        action='store_true', dest='debug', default=False,
        help="turn debug logging on")
# END - add_data_source_parameter


#=============================================================================
def test_for_parameter (parms, key):
    '''
    Description:
      Tests to see if a specific parameter is present.

    Returns:
       True - If the parameter is present in the dictionary
      False - If the parameter is *NOT* present in the dictionary or does not
              have a value
    '''

    if (not parms.has_key(key)) or (parms[key] == '') or (parms[key] == None):
        return False

    return True
# END - test_for_parameter


#=============================================================================
def convert_to_command_line_options (parms):
    '''
    Description:
      As simply stated in the routine name... Convert the JSON dictionary
      version of the parameters into command line parameters to use with the
      executables that will be called.
    '''

    options = ['--orderid', parms['orderid']]
    options += ['--scene', parms['scene']]

    for (key, value) in parms['options'].items():
        if value == True or value == False:
            options += ['--%s' % key]
        elif value != None:
            options += ['--%s' % key, '%s' % value]

    return options
# END - convert_parms_to_command_line_options

