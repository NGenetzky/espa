#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides a testing mechanism for packaging products.

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
from distribution import package_product


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

    parser.add_argument ('--product_name',
        action='store', dest='product_name', required=True,
        help="basename of the product to create")

    parser.add_argument ('--source_directory',
        action='store', dest='source_directory', default=os.curdir,
        help="directory on the localhost with the contents for packaging")

    parser.add_argument ('--destination_directory',
        action='store', dest='destination_directory', required=True,
        help="directory on the localhost to place the package")

    return parser
# END - build_argument_parser


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
        (product_full_path, cksum_full_path, cksum_value) = \
            package_product (args.source_directory, args.destination_directory,
            args.product_name)

        print ("Product Path: %s" % product_full_path)
        print ("Checksum Path: %s" % cksum_full_path)
        print ("Checksum Value: %s" % cksum_value)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

