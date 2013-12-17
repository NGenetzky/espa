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
from common.transfer import transfer_data


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
def distribute_product (destination_host, destination_directory,
  product_filename, cksum_filename):
    '''
    Descrription:
      Transfers the product and associated checksum to the specified directory
      on the destination host

    Note:
      It is assumed ssh has been setup for access between the localhost
      and destination system
    '''

    # Create the destination directory on the destination host
    log ("Creating destination directory %s on %s" \
        % (destination_directory, destination_host))
    cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', destination_host,
           'mkdir', '-p', destination_directory]
    subprocess.check_output (cmd)

    # Transfer the product file
    transfer_data('localhost', product_filename, destination_host,
        destination_directory)

    # Transfer the checksum file
    transfer_data('localhost', cksum_filename, destination_host,
        destination_directory)

    # Get the checksum value 
    cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-q', destination_host,
           'cksum', "%s/%s" % (destination_directory, \
                               os.path.basename(product_filename))]
    cksum_value = subprocess.check_output (cmd)

    return cksum_value
# END - distribute_product


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
        cksum_value = distribute_product (args.destination_host,
            args.destination_directory, args.product_filename,
            args.cksum_filename)

        print ("Checksum Value: %s" % cksum_value)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

