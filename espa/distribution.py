#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides methods for creating and distributing products.

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
from time import sleep
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, debug

# local objects and methods
from espa_exception import ErrorCodes, ESPAException
from transfer import transfer_data

# Define the number of seconds to sleep between attempts
default_sleep_seconds = 2


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
    current_directory = os.curdir
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
  product_filename, cksum_filename):
    '''
    Description:
      Transfers the product and associated checksum to the specified directory
      on the destination host

    Returns:
      cksum_value - The check sum value from the destination
      destination_full_path - The full path on the destination

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

    destination_full_path = '%s/%s' \
        % (destination_directory, os.path.basename(product_filename))

    # Get the checksum value 
    cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-q', destination_host,
           'cksum', destination_full_path]
    cksum_value = subprocess.check_output (cmd)

    return (cksum_value, destination_full_path)
# END - distribute_product


#==============================================================================
def deliver_product (work_directory, package_directory, product_name,
  destination_host, destination_directory, sleep_seconds=default_sleep_seconds,
  extract_statistics=False):
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
            (remote_cksum_value, destination_full_path) = \
                distribute_product (destination_host, destination_directory,
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
                % (product_full_path, destination_host, destination_full_path))

    if extract_statistics:
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-q', destination_host,
               'cd', destination_directory, ';',
               'tar', '-xf', destination_full_path, 'stats']
        cksum_value = subprocess.check_output (cmd)

    log ("Product delivery complete for %s:%s" % \
        (destination_host, destination_full_path))
# END - deliver_product

