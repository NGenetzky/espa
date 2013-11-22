
'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides routines for interfacing with parameters in a dictionary.

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

# espa-common objects and methods
from espa_constants import *
from espa_logging import log

#=============================================================================
def add_standard_parameters(parser):

    parser.add_argument('--orderid',
        action='store', dest='orderid', required=True,
        help="the order ID associated with this request")

    parser.add_argument('--scene',
        action='store', dest='scene', required=True,
        help="the scene ID associated with this request")

# END - add_standard_parameters

#=============================================================================
def test_for_parameter(parms, key):
    '''
    Description:
      Tests to see if a specific parameters is present.

    Returns:
       True - If the parameter is present in the dictionary
      False - If the parameter is *NOT* present in the dictionary or does not
              have a value
    '''

    if (not parms.has_key(key)) or (parms[key] == '') or (parms[key] == None):
        log ("Warning: Missing '%s' from parameters" % key)
        return False

    return True
# END - test_for_parameter

#=============================================================================
def convert_to_command_line_options(parms):
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

