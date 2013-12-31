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
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
import parameters
from distribution import distribute_product


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

    parser.add_argument ('--product_filename',
        action='store', dest='product_filename', required=True,
        help="basename of the product to distribute")

    parser.add_argument ('--cksum_filename',
        action='store', dest='cksum_filename', required=True,
        help="basename of the checksum file to distribute and verify")

    parameters.add_destination_parameters (parser)

    return parser
# END - build_argument_parser


#==============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read parameters from the command line and pass them to the main
      distribution routine.
    '''

    # Build the command line argument parser
    parser = build_argument_parser()

    # Parse the command line arguments
    args = parser.parse_args()

    # Setup debug
    set_debug (args.debug)

    try:
        # Call the main processing routine
        (cksum_value, destination_full_path) = \
            distribute_product (args.destination_host,
                args.destination_directory, args.product_filename,
                args.cksum_filename)

        print ("Delivered: %s:%s" \
            % (args.destination_host, destination_full_path))
        print ("Checksum Value: %s" % cksum_value)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

