#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Package up the contents of the specified directory and distribute it to the
  specified location.  Packaging will be tried three times before an exception
  is generated.  Distribution will be tried three times before an exception is
  generated.  If checksum validation fails, an exception is immediatly
  generated.  The caller is allowed to specify the number of seconds to sleep
  between each attempt.  The package consists of a tarball containing all the
  contents of the directory, and the tarball is then compressed using gzip.  A
  checksum file is generated on the *.tar.gz package and used for distribution
  validation.

  See package_product and distribute_product for additional details.

Notes:
  It is assumed that ssh keys have been setup between the localhost and
  destination systems.  Even if both systems are localhost, ssh is used for
  generating the checksum on the distributed package.

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
from espa_exception import ErrorCodes, ESPAException
import parameters
from package_product import package_product
from distribute_product import distribute_product


# Define the number of seconds to sleep between attempts
default_sleep_seconds = 2


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

    parser.add_argument ('--sleep_seconds',
        action='store', dest='sleep_seconds', default=default_sleep_seconds,
        help="number of seconds to sleep after a failure before retrying")

    return parser
# END - build_argument_parser


#==============================================================================
def deliver_product (work_directory, package_directory, product_name,
  destination_host, destination_directory, sleep_seconds=default_sleep_seconds):
    '''
    Description:
      Packages the product and distributes it to the destination.
      Verification of the local and remote checksum values is performed.

    Note:
        Three attempts are made for each part of the delivery
    '''

    max_number_of_attempts = 3

    # Package the product files
    # Attempt three times sleeping between each attempt
    attempt = 0
    while True:
        try:
            (product_full_path, cksum_full_path, local_cksum_value) = \
                package_product (work_directory, package_directory,
                    product_name)
        except Exception, e:
            log ("An error occurred processing %s" % scene)
            log ("Error: %s" % str(e))
            if attempt < max_number_of_attempts:
                sleep(sleep_seconds) # sleep before trying again
                attempt += 1
                continue
            else:
                raise ESPAException (ErrorCodes.packaging_product, str(e)), \
                    None, sys.exc_info()[2]
        break

    # Distribute the product
    # Attempt three times sleeping between each attempt
    attempt = 0
    while True:
        try:
            (remote_cksum_value, destination_full_path) = \
                distribute_product (destination_host, destination_directory,
                    product_full_path, cksum_full_path)
        except Exception, e:
            log ("An error occurred processing %s" % scene)
            log ("Error: %s" % str(e))
            if attempt < max_number_of_attempts:
                sleep(sleep_seconds) # sleep before trying again
                attempt += 1
                continue
            else:
                raise ESPAException (ErrorCodes.distributing_product, str(e)), \
                    None, sys.exc_info()[2]
        break

    # Checksum validation
    if local_cksum_value.split()[0] != remote_cksum_value.split()[0]:
        raise ESPAException (ErrorCodes.verifing_checksum,
            "Failed checksum validation between %s and %s:%s" \
                % (product_full_path, destination_host, destination_full_path))

    log ("Distribution complete for %s:%s" % \
        (destination_host, destination_full_path))
# END - deliver_product


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
            args.package_name, args.destination_host,
            args.destination_directory, args.sleep_seconds)

        print ("Succefully delivered product %s" % args.product_name)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

