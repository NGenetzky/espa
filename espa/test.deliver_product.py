#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides a testing mechanism for distributing products.

History:
  Created Dec/2013 by Ron Dilley, USGS/EROS
'''

import os
import sys
import traceback
from time import sleep
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
import parameters
from distribute import deliver_product


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
        action='store', dest='product_name', required=True,
        help="basename of the product to distribute")

    parameters.add_destination_parameters (parser)

    parser.add_argument ('--sleep_seconds',
        action='store', dest='sleep_seconds', default=default_sleep_seconds,
        help="number of seconds to sleep after a failure before retrying")

    parser.add_argument ('--extract_statistics',
        action='store_true', dest='extract_statistics', default=False,
        help="extract the statistics at the destination")

    return parser
# END - build_argument_parser


#==============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read parameters from the command line and pass them to the main
      delivery routine.
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
            args.product_name, args.destination_host,
            args.destination_directory, args.sleep_seconds,
            args.extract_statistics)

        print ("Succefully delivered product %s" % args.product_name)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

