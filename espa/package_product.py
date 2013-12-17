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
def package_product (source_directory, destination_directory, product_name):
    '''
    Descrription:
      Package the contents of the source directory into a gzipped tarball
      located in the destination directory and generate a checksum file

      The filename will be prefixed with the specified product name
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

