#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides methods for creating and distributing products.

History:
  Original Development (cdr_ecv.py) by David V. Hill, USGS/EROS
  Created Jan/2014 by Ron Dilley, USGS/EROS
    - Gutted the original implementation from cdr_ecv.py and placed it in this
      file.
'''

import os
import sys
import glob
import subprocess
import traceback
from time import sleep
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
from espa_exception import ErrorCodes, ESPAException
import parameters
from transfer import transfer_file

# Define the number of seconds to sleep between attempts
default_sleep_seconds = 2


#==============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser.
    '''

    # Create a command line argument parser
    description = "Provides methods for creating and distributing products"
    parser = ArgumentParser(description=description)

    # Parameters
    parameters.add_debug_parameter (parser)

    parser.add_argument ('--test_deliver_product',
        action='store_true', dest='test_deliver_product', default=False,
        help="test the delivery code which also tests package_product and" \
             " distribute_product")
    
    parser.add_argument ('--test_package_product',
        action='store_true', dest='test_package_product', default=False,
        help="test the packaging code")
    
    parser.add_argument ('--test_distribute_product',
        action='store_true', dest='test_distribute_product', default=False,
        help="test the distributing code")
    
    # Used by package and deliver and distribute
    parameters.add_destination_parameters (parser)

    # Used by package and deliver
    parser.add_argument ('--product_name',
        action='store', dest='product_name', required=False,
        help="basename of the product to distribute")

    # Used by deliver
    parameters.add_work_directory_parameter (parser)

    parser.add_argument ('--package_directory',
        action='store', dest='package_directory', default=os.curdir,
        help="package directory on the localhost")

    parser.add_argument ('--sleep_seconds',
        action='store', dest='sleep_seconds', default=default_sleep_seconds,
        help="number of seconds to sleep after a failure before retrying")

    # Used by distribute
    parser.add_argument ('--product_file',
        action='store', dest='product_file', required=False,
        help="full path of the product to distribute")

    parser.add_argument ('--cksum_file',
        action='store', dest='cksum_file', required=False,
        help="full path of the checksum file to distribute and verify")

    return parser
# END - build_argument_parser


#==============================================================================
def package_product (source_directory, destination_directory, product_name):
    '''
    Description:
      Package the contents of the source directory into a gzipped tarball
      located in the destination directory and generates a checksum file for it

      The filename will be prefixed with the specified product name

    Returns:
      product_full_path - The full path to the product including filename
      cksum_full_path - The full path to the check sum including filename
      cksum_value - The checksum value
    '''

    product_full_path = os.path.join(destination_directory, product_name)

    # Remove any old products from the destination directory
    old_product_list = glob.glob("%s*" % product_full_path)
    for old_product in old_product_list:
        os.unlink(old_product)

    # Change to the source directory
    current_directory = os.getcwd()
    os.chdir(source_directory)

    try:
        # Tar the files
        log ("Packaging completed product to %s.tar.gz" % product_full_path)
        product_files = glob.glob("*")
        cmd = ['tar', '-cf', '%s.tar' % product_full_path]
        cmd += product_files
        subprocess.check_output (cmd)

        # It has the tar extension now
        product_full_path = "%s.tar" % product_full_path

        # Compress the product tar
        cmd = ['gzip', product_full_path]
        subprocess.check_output (cmd)

        # It has the gz extension now
        product_full_path = "%s.gz" % product_full_path

        # Change file permissions 
        log ("Changing file permissions on %s to 0644" % (product_full_path))
        os.chmod(product_full_path, 0644)

        # Verify that the archive is good
        cmd = ['tar', '-tf', product_full_path]
        subprocess.check_output (cmd)

        # If it was good then create a checksum file
        cmd = ['cksum', product_full_path]
        output = subprocess.check_output (cmd)

        # Name of the checksum file created
        cksum_filename = "%s.cksum" % product_name
        # Get the base filename of the file that was checksum'd
        cksum_prod_filename = os.path.basename(product_full_path)

        debug ("Checksum file = %s" % cksum_filename)
        debug ("Checksum'd file = %s" % cksum_prod_filename)

        output = output.split()
        cksum_value = str("%s %s %s") \
            % (str(output[0]), str(output[1]), str(cksum_prod_filename))
        log ("Generating cksum:%s" % cksum_value)

        cksum_full_path = os.path.join(destination_directory, cksum_filename)

        cksum_fd = open(cksum_full_path, 'wb+')
        cksum_fd.write(cksum_value)
        cksum_fd.flush()
        cksum_fd.close()
 
    finally:
        # Change back to the previous directory
        os.chdir(current_directory)

    return (product_full_path, cksum_full_path, cksum_value)
# END - package_product


#==============================================================================
def distribute_product (destination_host, destination_directory,
  destination_username, destination_pw,
  product_filename, cksum_filename):
    '''
    Description:
      Transfers the product and associated checksum to the specified directory
      on the destination host

    Returns:
      cksum_value - The check sum value from the destination
      destination_product_file - The full path on the destination

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

    # Transfer the checksum file
    destination_cksum_file = '%s/%s' \
        % (destination_directory, os.path.basename(cksum_filename))
    transfer_file('localhost', cksum_filename, destination_host,
        destination_cksum_file, destination_username=destination_username,
        destination_pw=destination_pw)

    # Transfer the product file
    destination_product_file = '%s/%s' \
        % (destination_directory, os.path.basename(product_filename))
    transfer_file('localhost', product_filename, destination_host,
        destination_product_file, destination_username=destination_username,
        destination_pw=destination_pw)

    # Get the remote checksum value 
    cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-q', destination_host,
           'cksum', destination_product_file]
    cksum_value = subprocess.check_output (cmd)

    return (cksum_value, destination_product_file)
# END - distribute_product


#==============================================================================
def deliver_product (work_directory, package_directory, product_name,
  destination_host, destination_directory,
  destination_username, destination_pw,
  sleep_seconds=default_sleep_seconds):
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
            log ("An error occurred processing %s" % product_name)
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
            (remote_cksum_value, destination_product_file) = \
                distribute_product (destination_host, destination_directory,
                    destination_username, destination_pw,
                    product_full_path, cksum_full_path)
        except Exception, e:
            log ("An error occurred processing %s" % product_name)
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
                % (product_full_path, destination_host, destination_product_file))

    log ("Product delivery complete for %s:%s" % \
        (destination_host, destination_product_file))
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
        # Test requested routine
        if args.test_deliver_product:

            if not args.product_name:
                raise Exception("Missing required product_name argument")

            deliver_product (args.work_directory, args.package_directory,
                args.product_name, args.destination_host,
                args.destination_directory, args.destination_host,
                args.destination_pw, args.sleep_seconds)

            print ("Succefully delivered product %s" % args.product_name)

        elif args.test_package_product:
            (product_full_path, cksum_full_path, cksum_value) = \
                package_product (args.work_directory,
                    args.destination_directory, args.product_name)

            print ("Product Path: %s" % product_full_path)
            print ("Checksum Path: %s" % cksum_full_path)
            print ("Checksum Value: %s" % cksum_value)
            print ("Succefully packaged product %s" % args.product_name)

        elif args.test_distribute_product:
            (cksum_value, destination_full_path) = \
                distribute_product (args.destination_host,
                    args.destination_directory, args.destination_host,
                    args.destination_pw, args.product_file, args.cksum_file)
            print ("Succefully distributed product %s" % args.product_file)

    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

