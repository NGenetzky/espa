#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  This module provides routines to be used for analyzing and manipulating tile
  data.

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import sys
import numpy as np
from argparse import ArgumentParser

from espa_constants import *
from espa_logging import log

NO_DATA_VALUE = -9999 # TODO TODO TODO - Maybe move this to espa_constants

def tile_statistics(tile_data, min_flag=False, max_flag=False, avg_flag=False,
                    stddev_flag=False, all_flag=False):
    '''
    Description:
      Take an input data array and remove the NO_DATA_VALUE from its contents.
      Then using numpy perform the requested statistics and return the results.

    Returns:
      An array of values is always returned in the following order.
        - minimum: The minimum value in the tile data.
        - maximum: The maximum value in the tile data.
        - average: The average value in the tile data.
        - stddev: The standard deviation of the tile data.
    '''

    tile_data_reduced = \
        np.ma.masked_equal(tile_data, NO_DATA_VALUE).compressed()

    minimum = NO_DATA_VALUE
    if all_flag or min_flag:
        minimum = tile_data_reduced.min()

    maximum = NO_DATA_VALUE
    if all_flag or max_flag:
        maximum = tile_data_reduced.max()

    average = NO_DATA_VALUE
    if all_flag or avg_flag:
        average = tile_data_reduced.mean()

    stddev = NO_DATA_VALUE
    if all_flag or stddev_flag:
        stddev = tile_data_reduced.std()

    pixel_count = len(tile_data_reduced)

    return (minimum, maximum, average, stddev, pixel_count)
# END - tile_statistics


'''
TODO TODO TODO - Need to add more of these data types in to the processing
TODO TODO TODO - Need to add more of these data types in to the processing
TODO TODO TODO - Need to add more of these data types in to the processing
TODO TODO TODO - Need to add more of these data types in to the processing

np.bool         Boolean (True or False) stored as a byte
np.int          Platform integer (normally either int32 or int64)
np.int8         Byte (-128 to 127)
np.int16        Integer (-32768 to 32767)
np.int32        Integer (-2147483648 to 2147483647)
np.int64        Integer (9223372036854775808 to 9223372036854775807)
np.uint8        Unsigned integer (0 to 255)
np.uint16       Unsigned integer (0 to 65535)
np.uint32       Unsigned integer (0 to 4294967295)
np.uint64       Unsigned integer (0 to 18446744073709551615)
np.float        Shorthand for float64.
np.float16      Half precision float: sign bit, 5 bits exponent, 10 bits
                mantissa
np.float32      Single precision float: sign bit, 8 bits exponent, 23 bits
                mantissa
np.float64      Double precision float: sign bit, 11 bits exponent, 52 bits
                mantissa
np.complex      Shorthand for complex128.
np.complex64    Complex number, represented by two 32-bit floats
                (real and imaginary components)
np.complex128   Complex number, represented by two 64-bit floats
                (real and imaginary components)
'''
#=============================================================================
if __name__ == '__main__':
    '''
    Description:
      If running this script manually provides arguments on the command line
      for analyzing tiles.
    '''

    # Create a command line argument parser
    parser = ArgumentParser(usage="%(prog)s [options]")

    parser.add_argument('--tile', '--tile_filename',
        action='append', dest='tiles',
        help="specify tiles to be processed; can specify multiple on the" \
            " command line")

    parser.add_argument('--all_stats',
        action='store_true', dest='all_stats', default=True,
        help="determine all the statistics for each specified tile")

    parser.add_argument('--min', '--minimum',
        action='store_true', dest='minimum',
        help="determine the minimum value for each specified tile")

    parser.add_argument('--max', '--maximum',
        action='store_true', dest='maximum',
        help="determine the maximum value for each specified tile")

    parser.add_argument('--avg', '--average',
        action='store_true', dest='average',
        help="determine the average value for each specified tile")

    parser.add_argument('--std', '--stddev',
        action='store_true', dest='stddev',
        help="determine the standard deviation value for each specified tile")

    # Parse the command line
    args = parser.parse_args()

    # Verify that some tiles are present
    if args.tiles == None:
        log ("Missing '--tile' parameters for processing")
        sys.exit(EXIT_FAILURE)

    # Get the count of tiles to help with later processing
    tile_count = len(args.tiles)

    if args.minimum or args.maximum or args.average or args.stddev:
        args.all_stats = False

    # Generate the requested statistics for each tile
    for tile in args.tiles:
        fd = open(tile, 'rb')
        tile_data = np.fromfile(file=fd, dtype=np.int16)
        fd.close()

        (minimum, maximum, average, stddev, pixel_count) = \
            tile_statistics(tile_data, min_flag=args.minimum,
                max_flag=args.maximum, avg_flag=args.average,
                stddev_flag=args.stddev, all_flag=args.all_stats)

        print "Tile Stats: %s" % tile
        print "  Pixel Count: %d" % pixel_count
        if args.all_stats or args.minimum:
            print "  Minimum: %f" % minimum
        if args.all_stats or args.maximum:
            print "  Maximum: %f" % maximum
        if args.all_stats or args.average:
            print "  Average: %f" % average
        if args.all_stats or args.stddev:
            print "  Standard Deviation: %f" % stddev
    # END - for tile

    sys.exit(EXIT_SUCCESS)
# END - __main__

