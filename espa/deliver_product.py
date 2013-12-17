#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  See 'Description' under '__main__' for more details.
  TODO TODO TODO

History:
  Original Development (cdr_ecv.py) by David V. Hill, USGS/EROS
  Created Dec/2013 by Ron Dilley, USGS/EROS
    - Gutted the original implementation from cdr_ecv.py and placed it in this
      file.
'''

import os
import sys
import glob
import subprocess
import traceback
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
import common.parameters as parameters
from package_product import package_product
from distribute_product import distribute_product


#==============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser.
    '''

    # Create a command line argument parser
    parser = ArgumentParser(usage="%(prog)s [options]")

    # Parameters
    parameters.add_debug_parameter (parser)

    parameters.add_work_directory_parameter (parser)

    parser.add_argument ('--package_directory',
        action='store', dest='package_directory', default=os.curdir,
        help="directory to place the package on the localhost")

    parser.add_argument ('--product_name',
        action='store', dest='product_filename', required=True,
        help="basename of the product to distribute")

    parameters.add_destination_parameters (parser)

    return parser
# END - build_argument_parser


#==============================================================================
def deliver_product (work_directory, package_directory, product_name,
  destination_host, destination_directory):
    '''
    Descrription:
      Packages the product and distributes it to the destination.
      Verification of the checksum values is also performed.
    '''

    # Package the product files
    # Attempt three times sleeping between each attempt
    attempt = 0
    while True:
        try:
            (product_full_path, cksum_full_path, cksum_value) = \
                package_product (work_directory, package_directory,
                    product_name)
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

    # Distribute the product
    # Attempt three times sleeping between each attempt
    attempt = 0
    while True:
        try:
            cksum_value = distribute_product (destination_host,
                destination_directory, product_full_path, cksum_full_path)
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

    # TODO TODO TODO - Compare the checksum values

# END - deliver_product


#==============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read parameters from the command line and pass them to the main
      packaging routine.
    '''

    # Build the command line argument parser
    parser = build_argument_parser()

    # Parse the command line arguments
    args = parser.parse_args()

    # Setup debug
    set_debug (args.debug)

    try:
        # Call the main processing routine
        deliver_product (args.work_directory, args.package_directory,
            args.package_name, args.destination_host,
            args.destination_directory)

    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

