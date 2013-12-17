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
import traceback

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, debug

# local objects and methods
from common.directory_tools import initialize_processing_directory
from common.transfer import stage_landsat_data
from common.packaging import untar_data
import common.parameters as parameters
from build_science_products import build_landsat_science_products, \
    validate_build_landsat_parameters
import warp_science_products as warp
from deliver_product import deliver_product
import common.util as util


#==============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser.
    '''

    # Create a command line argument parser
    parser = ArgumentParser (usage="%(prog)s [options]")

    # Parameters
    parameters.add_debug_parameter (parser)

    parameters.add_orderid_parameter (parser)

    parameters.add_scene_parameter (parser)

    parameters.add_data_type_parameter (parser, parameters.valid_data_types)

    parameters.add_source_parameters (parser)
    parameters.add_destination_parameters (parser)

    parameters.add_reprojection_parameters (parser, warp.valid_projections,
        warp.valid_utm, warp.valid_pixel_units, warp.valid_resample_methods)

    parameters.add_science_product_parameters (parser)

    parameters.add_include_statistics_parameter (parser)

    return parser
# END - build_argument_parser


#==============================================================================
def validate_parameters (parms):
    '''
    Description:
      Make sure all the parameter options needed for this and called routines
      is available with the provided input parameters.
    '''

    # Test for presence of top-level parameters
    keys = ['orderid', 'scene', 'options']
    for key in keys:
        if not parameters.test_for_parameter (parms, key):
            raise RuntimeError ("Missing required input parameter [%s]" % key)

    options = parms['options']

    # Test for presence of required option-level parameters
    keys = ['source_host',
            'source_directory',
            'destination_host',
            'destination_directory']

    for key in keys:
        if not parameters.test_for_parameter (options, key):
            raise RuntimeError ("Missing required input parameter [%s]" % key)

    # Validate the science product parameters
    validate_build_landsat_parameters (parms)

    # Validate the reprojection parameters
    parameters.validate_reprojection_parameters (options,
        warp.valid_projections, warp.valid_utm, warp.valid_pixel_units,
        warp.valid_resample_methods)

    # Force these parameters to false if not provided
    keys = ['include_statistics']

    for key in keys:
        if not parameters.test_for_parameter (options, key):
            options[key] = False

    # Extract the sensor from the scene string
    sensor = util.getSensor(parms['scene'])

    if sensor not in parameters.valid_sensors:
        raise NotImplementedError ("Data sensor %s is not implemented" % \
            sensor)

    # Add the sensor to the options
    options['sensor'] = sensor
# END - validate_parameters


#==============================================================================
def build_product_name (scene):
    '''
    Description:
      Build the product name from the scene information and current time.
    '''

    # Get the current time information
    ts = datetime.today()

    # Extract stuff from the scene
    sensor_code = util.getSensorCode(scene)
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


#==============================================================================
def process (parms):
    '''
    Description:
      Provides the processing for the generation of the science products and
      then processing them through the statistics generation.
    '''

    # Validate the parameters
    validate_parameters (parms)

    # Convert to command line parameters
    cmd_options = parameters.convert_to_command_line_options (parms)

    scene = parms['scene']

    # Create and retrieve the directories to use for processing
    (scene_directory, stage_directory, work_directory, package_directory) = \
        initialize_processing_directory (parms['orderid'], scene)

    # Keep a local options for those apps that only need a few things
    options = parms['options']
    sensor = options['sensor']

    # Add the work directory to the parameters
    options['work_directory'] = work_directory

    # Figure out the product name
    product_name = build_product_name(scene)

    metadata = None
    filename = None

    # Stage the landsat data
    filename = stage_landsat_data(scene, options['source_host'],
        options['source_directory'], 'localhost', stage_directory)

    # Un-tar the input data to the work directory
    untar_data (filename, work_directory)

    # Build the requested science products
    build_landsat_science_products (parms)

    # Reproject the data for each science product, but only if necessary
    # TODO TODO TODO - In the future the (image extents)tile processing
    # should be capable of only containing the information contained
    # within a requested polygon
    if options['reproject'] or options['resize'] or options['image_extents']:
        warp.warp_science_products (options)

    # TODO TODO TODO - Generate the stats for each stat'able'
    #                  science product
    #cmd = ['generate_stats.py']
    #cmd += cmd_options

    # Deliver the product files
    # Attempt three times sleeping between each attempt
    attempt = 0
    while True:
        try:
            deliver_product (work_directory, package_directory, product_name,
                options['destination_host'], options['destination_directory'])
        except Exception, e:
            log ("An error occurred processing %s" % scene)
            log ("Error: %s" % str(e))
            if attempt < 3:
                sleep(15) # 15 seconds and try again
                attempt += 1
                continue
            else:
                raise e
        break
# END - process


#==============================================================================
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
    parms['orderid'] = orderid
    parms['scene'] = scene
    parms['options'] = options

    # Call the process routine with the JSON parameters
    try:
        process (parms)
    except Exception, e:
        log ("An error occurred processing %s" % sceneid)
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

