#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description: TODO TODO TODO

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import sys
import json
import subprocess
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log

# local objects and methods
from common.directory_tools import initialize_processing_directory
from common.transfer import stage_input_data
from common.packaging import unpack_data
import common.parameters as parameters
from common.metadata import get_metadata


#=============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser.
    '''

    # Create a command line argument parser
    parser = ArgumentParser (usage="%(prog)s [options]")

    # Add the standard parameters
    parameters.add_standard_parameters (parser)

    # Add specific parameters
    parameters.add_data_source_parameter (parser,
        parameters.valid_data_sources)

    parser.add_argument ('--source_host',
        action='store', dest='source_host', default='localhost',
        help="source host for the location of the data")

    parser.add_argument ('--source_directory',
        action='store', dest='source_directory', default='.',
        help="directory on the source host")

    parser.add_argument ('--destination_host',
        action='store', dest='destination_host', default='localhost',
        help="destination host for the processing results")

    parser.add_argument ('--destination_directory',
        action='store', dest='destination_directory', default='.',
        help="directory on the destination host")

    parser.add_argument ('--include_sr',
        action='store_true', dest='include_sr', default=False,
        help="process statistics on SR data")

    parser.add_argument ('--include_sr_toa',
        action='store_true', dest='include_sr_toa', default=False,
        help="process statistics on SR TOA data")

    parser.add_argument ('--include_sr_thermal',
        action='store_true', dest='include_sr_thermal', default=False,
        help="process statistics on SR Thermal data")

    parser.add_argument ('--include_sr_nbr',
        action='store_true', dest='include_sr_nbr', default=False,
        help="process statistics on SR NBR data")

    parser.add_argument ('--include_sr_nbr2',
        action='store_true', dest='include_sr_nbr2', default=False,
        help="process statistics on SR NBR2 data")

    parser.add_argument ('--include_sr_ndvi',
        action='store_true', dest='include_sr_ndvi', default=False,
        help="process statistics on SR NDVI data")

    parser.add_argument ('--include_sr_ndmi',
        action='store_true', dest='include_sr_ndmi', default=False,
        help="process statistics on SR NDMI data")

    parser.add_argument ('--include_sr_savi',
        action='store_true', dest='include_sr_savi', default=False,
        help="process statistics on SR SAVI data")

    parser.add_argument ('--include_sr_evi',
        action='store_true', dest='include_sr_evi', default=False,
        help="process statistics on SR EVI data")

    parser.add_argument ('--lpvs_minimum',
        action='store_true', dest='lpvs_minimum', default=False,
        help="compute minimum value for each specified dataset")

    parser.add_argument ('--lpvs_maximum',
        action='store_true', dest='lpvs_maximum', default=False,
        help="compute maximum value for each specified dataset")

    parser.add_argument ('--lpvs_average',
        action='store_true', dest='lpvs_average', default=False,
        help="compute average value for each specified dataset")

    parser.add_argument ('--lpvs_stddev',
        action='store_true', dest='lpvs_stddev', default=False,
        help="compute standard deviation value for each specified dataset")

    return parser
# END - build_argument_parser


#=============================================================================
def validate_input_parameters (parms):
    '''
    Description:
      Make sure all the parameter options needed for this and called routines
      is available with the provided input parameters.
    '''

    # Test for presence of top-level parameters
    keys = ['orderid', 'scene', 'options']
    for key in keys:
        if not parameters.test_for_parameter (parms, key):
            return ERROR

    # Test for presence of required option-level parameters
    keys = ['data_source', 'source_host', 'source_directory',
            'destination_host', 'destination_directory', 'include_sr',
            'include_sr_toa', 'include_sr_thermal', 'include_sr_nbr',
            'include_sr_nbr2', 'include_sr_ndvi', 'include_sr_ndmi',
            'include_sr_savi', 'include_sr_evi', 'lpvs_minimum',
            'lpvs_maximum', 'lpvs_average', 'lpvs_stddev']

    for key in keys:
        if not parameters.test_for_parameter (parms['options'], key):
            return ERROR

    # Test specific parameters for acceptable values if needed
    options = parms['options']

    if options['data_source'] not in parameters.valid_data_sources:
        raise Exception ("Error: Unsupported data_source [%s]" % \
            options['data_source'])
    # TODO TODO TODO TODO TODO TODO TODO TODO - Add more

# END - validate_input_parameters


#=============================================================================
def process (parms):
    '''
    Description:
      Provides the processing for the generation of the science products and
      then processing them through the statistics generation.
    '''

    cmd_options = parameters.convert_to_command_line_options (parms)

    scene = parms['scene']

    # Create and retrieve the directories to use for processing
    try:
        (scene_directory, stage_directory, work_directory, output_directory) = \
            initialize_processing_directory (scene)
    except Exception, e:
        log ("Error: Failed creating processing directory")
        log (str(e))
        return ERROR

    # Keep a local options for those apps that only need a few things
    options = parms['options']
    data_source = options['data_source']

    metadata = None
    filename = None
    try:
        # Stage the input data
        # TODO TODO TODO - Maybe in the future we don't care about source and host because we look it up in a service?????????????????????????
        filename = stage_input_data(data_source, scene,
            options['source_host'], options['source_directory'],
            'localhost', stage_directory)

        # Unpack the input data to the work directory
        unpack_data (data_source, filename, work_directory)

        # Get metadata information
        metadata = get_metadata (data_source, work_directory)
    except ValueError, e:
        log ("Error: %s" % e.message)
        raise

    # TODO TODO TODO
    # Probably need to change to the work directory somewhere
    # A bunch of the following also gets placed into the above try/except
    # TODO TODO TODO

    # build_science_products Landsat Science Products
    if data_source == 'landsat':
        # TODO - ?? convert to internal binary format first ??
        cmd = ['build_science_products.py']
        cmd += cmd_options

        # TODO TODO TODO
        #print cmd
        #print ''
    elif data_source == 'landsat':
        # TODO - ?? convert to internal binary format first ??
        x = 'y'

    # Generate the tile data for each science product
    cmd = ['generate_tiles.py']
    cmd += cmd_options

    # TODO TODO TODO
    #print cmd
    #print ''

    # Generate the stats for each tile
    cmd = ['generate_stats.py']
    cmd += cmd_options

    # TODO TODO TODO
    #print cmd
    #print ''

    # Transfer the product data to the on-line product cache
    # transfer.py  TODO TODO TODO

    # update_order_status
    cmd = ['update_order_status.py']
    cmd += ['--orderid', parms['orderid']]
    cmd += ['--scene', parms['scene']]
    cmd += ['--order_status', 'LPVS_STATS_COMPLETE']

    # TODO TODO TODO
    #print cmd
    #print ''

    return SUCCESS
# END - process


#=============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read parameters from the command line and build a JSON dictionary from
      them.  Pass the JSON dictionary to the process routine.
    '''

    # Create the JSON dictionary to use
    json_parms = dict()

    # Build the command line argument parser
    parser = build_argument_parser()

    # Parse the arguments and place them into a dictionary
    args_dict = vars(parser.parse_args())

    # Build our JSON formatted input from the command line parameters
    orderid = args_dict.pop ('orderid')
    scene = args_dict.pop ('scene')
    options = {k : args_dict[k] for k in args_dict if args_dict[k] != None}

    # Build the JSON parameters dictionary
    json_parms['orderid'] = orderid
    json_parms['scene'] = scene
    json_parms['options'] = options

    # Validate the JSON parameters
    try:
        validate_input_parameters (json_parms)
    except Exception, e:
        log (str(e))
        sys.exit (EXIT_FAILURE)

    # Call the process routine with the JSON parameters
    if process (json_parms) != SUCCESS:
        log ("Error processing LPVS")

    sys.exit (EXIT_SUCCESS)

