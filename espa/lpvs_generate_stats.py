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
import re
import json
from time import sleep
from datetime import datetime
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, debug

# local objects and methods
from common.directory_tools import initialize_processing_directory
from common.transfer import stage_input_data
from common.packaging import unpack_data
import common.parameters as parameters
from build_science_products import build_science_products
from warp_science_products import warp_science_products
from package_product import package_product
import util


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
    parameters.add_data_type_parameter (parser, parameters.valid_data_types)

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

    parser.add_argument ('--stats_minimum',
        action='store_true', dest='stats_minimum', default=False,
        help="compute minimum value for each specified dataset")

    parser.add_argument ('--stats_maximum',
        action='store_true', dest='stats_maximum', default=False,
        help="compute maximum value for each specified dataset")

    parser.add_argument ('--stats_average',
        action='store_true', dest='stats_average', default=False,
        help="compute average value for each specified dataset")

    parser.add_argument ('--stats_stddev',
        action='store_true', dest='stats_stddev', default=False,
        help="compute standard deviation value for each specified dataset")

    parameters.add_debug_parameter (parser)

    return parser
# END - build_argument_parser


#=============================================================================
def validate_input_parameters (parms):
    '''
    Description:
      Make sure all the parameter options needed for this and called routines
      is available with the provided input parameters.
    '''
# TODO TODO TODO - xmlrpc needs to be figured out.....................
# TODO TODO TODO - xmlrpc needs to be figured out.....................
# TODO TODO TODO - xmlrpc needs to be figured out.....................
# TODO TODO TODO - xmlrpc needs to be figured out.....................
    # Test for presence of top-level parameters
    keys = ['orderid', 'scene', 'options']
    for key in keys:
        if not parameters.test_for_parameter (parms, key):
            raise RuntimeError ("Missing required input parameter [%s]" % key)

    # Test for presence of required option-level parameters
    keys = ['data_type',
            'source_host',
            'source_directory',
            'destination_host',
            'destination_directory']

    options = parms['options']

    for key in keys:
        if not parameters.test_for_parameter (options, key):
            raise RuntimeError ("Missing required input parameter [%s]" % key)

    # Test specific parameters for acceptable values if needed
    data_type = options['data_type']

    if data_type not in parameters.valid_data_types:
        raise NotImplementedError ("Unsupported data_type [%s]" % data_type)

    # Extract the sensor from the scene string
    sensor_code = parms['scene'][0:3]
    sensor = re.search('^([A-Za-z]+).', sensor_code).group(1)

    if sensor not in parameters.valid_sensors:
        raise NotImplementedError ("Data sensor %s is not implemented" % \
            sensor)

    # Add the sensor to the options
    options['sensor'] = sensor
    options['sensor_code'] = sensor_code

    # TODO TODO TODO TODO TODO TODO TODO TODO - Add more
    # TODO TODO TODO TODO TODO TODO TODO TODO - Add more
    # TODO TODO TODO TODO TODO TODO TODO TODO - Add more

# END - validate_input_parameters


#=============================================================================
# TODO TODO TODO - This should probably be in a library somewhere
def build_product_name (sensor_code, scene):
    '''
    Description:
      Build  the product name from the current time and the scene.
    '''

    # Get the current time information
    ts = datetime.today()

    # Extract stuff from the scene
    path = util.getPath(scene)
    row = util.getRow(scene)
    year = util.getYear(scene)
    doy = util.getDoy(scene)

    product_name = "%s%s%s%s%s-SC%s%s%s%s%s%s" \
        % (sensor_code, path.zfill(3), row.zfill(3), year.zfill(4),
           doy.zfill(3), str(ts.year).zfill(4), str(ts.month).zfill(2),
           str(ts.day).zfill(2), str(ts.hour).zfill(2),
           str(ts.minute).zfill(2), str(ts.second).zfill(2))

    return product_name
# END - build_product_name


#=============================================================================
def process (parms):
    '''
    Description:
      Provides the processing for the generation of the science products and
      then processing them through the statistics generation.
    '''

    # Validate the parameters
    try:
        validate_input_parameters (parms)
    except Exception, e:
        log ("Error: %s" % str(e))
        return ERROR

    # Convert to command line parameters
    cmd_options = parameters.convert_to_command_line_options (parms)

    scene = parms['scene']

    # Create and retrieve the directories to use for processing
    try:
        (scene_directory, stage_directory, work_directory, output_directory) = \
            initialize_processing_directory (parms['orderid'], scene)
    except Exception, e:
        log ("Error: %s" % str(e))
        return ERROR

    # Add the work directory to the parameters
    parms['work_directory'] = work_directory

    # Keep a local options for those apps that only need a few things
    options = parms['options']
    sensor = options['sensor']

    # Figure out the product name
    product_name = build_product_name(options['sensor_code'], scene)

    metadata = None
    filename = None
    try:
        # Stage the input data TODO TODO TODO - Change to a list of files
        filename = stage_input_data(sensor, scene,
            options['source_host'], options['source_directory'],
            'localhost', stage_directory)

        # Unpack the input data to the work directory
        unpack_data (sensor, filename, work_directory)

        # Build the requested science products
        build_science_products (parms)

        # Reproject the data for each science product, but only if necessary
        # TODO - Should this also tile the data and (TODO) in the future the
        # tile will only contain the information contained within the
        # requested polygon
        if options['reproject'] or options['pixel_size'] \
          or options['image_extents']:
            warp_science_products (parms)

        # TODO - Generate the stats for each stat'able' science product
        #cmd = ['generate_stats.py']
        #cmd += cmd_options

        # Package the product files
        # Attempt three times sleeping between each attempt
        attempt = 0
        while True:
            try:
                (product_full_path, cksum_full_path, cksum_value) = \
                    package_product (work_directory, output_directory,
                        product_name)
            except Exception, e:
                if attempt < 3:
                    sleep(15) # 15 seconds and try again
                    continue
                else:
                    raise e
            break

        # TODO - Distribute the product
        # transfer.py

    except Exception, e:
        log ("Error: %s" % str(e))
        log ("Error: Output [%s]" % e.output)
        return ERROR

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
    args = parser.parse_args()
    args_dict = vars(args)

    # Setup debug
    set_debug (args.debug)

    # Build our JSON formatted input from the command line parameters
    orderid = args_dict.pop ('orderid')
    scene = args_dict.pop ('scene')
    options = {k : args_dict[k] for k in args_dict if args_dict[k] != None}

    # Build the JSON parameters dictionary
    json_parms['orderid'] = orderid
    json_parms['scene'] = scene
    json_parms['options'] = options

    # Call the process routine with the JSON parameters
    if process (json_parms) != SUCCESS:
        log ("Error processing LPVS")

    sys.exit (EXIT_SUCCESS)

