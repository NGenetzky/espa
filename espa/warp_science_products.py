#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  See 'Description' under '__main__' for more details.
  Alters product extents, projections and pixel sizes.

History:
  Original Development (cdr_ecv.py) by David V. Hill, USGS/EROS
  Created Dec/2013 by Ron Dilley, USGS/EROS
    - Gutted the original implementation from cdr_ecv.py and placed it in this
      file.
'''

import os
import sys
import subprocess
import glob
from cStringIO import StringIO

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
import common.parameters as parameters
from common.metadata import get_metadata

# This contains the valid sensors which are supported
valid_landsat_sensors = ['LT', 'LE']
valid_modis_sensors = ['MODIS']
valid_science_sensors = valid_landsat_sensors + valid_modis_sensors

valid_resample_methods = ['near', 'bilinear', 'cubic', 'cubicspline', 'lanczos']
valid_pixel_units = ['meters', 'dd']

#=============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser.
    '''

    # Create a command line argument parser
    parser = ArgumentParser(usage="%(prog)s [options]")

    # Add the standard parameters
    add_standard_parameters(parser)

    # Add specific parameters
    parser.add_argument("--resample_method",
        action="store", dest="resample_method", default="near",
        choices=valid_resample_methods,
        help="one of %s" % ", ".join(valid_resample_methods))

    # TODO TODO TODO - Add resample parameters

    parser.add_argument("--pixel_units",
        action="store", dest="pixel_units", default="meters",
        choices=valid_pixel_units,
        help="one of %s" % ", ".join(valid_pixel_units))

    # TODO TODO TODO - Add pixel_size

    return parser
# END - build_argument_parser

#=============================================================================
def validate_parameters (parms):
    '''
    Description:
      Make sure all the parameter options needed for this and called routines
      is available with the provided input parameters.
    '''

    # Test for presence of top-level parameters
    keys = ['orderid', 'scene', 'options']
    for key in keys:
        if not parameters.test_for_parameter (parms, key):
            return ERROR

    # Access to the options parameters
    options = parms['options']

    # Test for presence of required option-level parameters
    keys = ['data_type']

    for key in keys:
        if not parameters.test_for_parameter (options, key):
            return ERROR

    # Test specific parameters for acceptable values if needed
    if options['data_type'] not in parameters.valid_data_types:
        raise NotImplementedError ("Unsupported data_type [%s]" % \
            options['data_type'])

    # Force these parameters to false if not provided
    # TODO TODO TODO - add others
    keys = ['include_sr', 'include_sr_browse', 'include_sr_toa',
            'include_sr_thermal', 'include_sr_nbr', 'include_sr_nbr2',
            'include_sr_ndvi', 'include_sr_ndmi', 'include_sr_savi',
            'include_sr_evi', 'include_snow_covered_area',
            'include_surface_water_extent', 'create_dem']

    for key in keys:
        if not parameters.test_for_parameter (options, key):
            options[key] = False

    
    if parameters.test_for_parameter (options, 'resample_method'):
        if options['resample_method'] not in valid_resample_methods:
            raise NotImplementedError ("Unsupported resample_method [%s]" % \
                options['resample_method'])
        # TODO - Test for resample parameters

    if parameters.test_for_parameter (options, 'pixel_units'):
        if options['pixel_units'] not in valid_pixel_units:
            raise NotImplementedError ("Unsupported pixel_units [%s]" % \
                options['pixel_units'])
        # TODO - Test for pixel_size parameter

    #if parameters.test_for_parameter (options, 'image_extents'):
        # TODO - Test for image_extents parameters

# END - validate_parameters


#=============================================================================
def build_warp_command (source_file, output_file,
  min_x=None, min_y=None, max_x=None, max_y=None,
  pixel_size=None, projection=None, resample_method=None):
    '''
    Description:
      Builds the GDAL warp command to convert the data
    '''

    cmd = ['gdalwarp', '-wm', '2048', '-multi']

    # Subset the image using the specified extents
    if (min_x is not None) and (min_y is not None) \
      and (max_x is not None) and (max_y is not None):
        cmd += ['-te', float(minx.strip()), float(miny.strip()),
                float(maxx.strip()), float(maxy.strip())]

    # Resize the pixels
    if pixel_size is not None:
        cmd += ['-tr', pixel_size, pixel_size]

    # Reproject the data
    if projection is not None:
        cmd += ['-t_srs', projection]

    # Specify the resampling method
    if resample_method is not None:
        cmd += ['-r', resample_method]

    cmd += [source_file, output_file]

    return cmd
# END - build_warp_command


#=============================================================================
def parse_hdf_subdatasets (hdf_file):
    '''
    Description:
      Finds all the subdataset names in an hdf file
    '''

    cmd = ['gdalinfo', hdf_file]
    output = subprocess.check_output (cmd)
    for line in output.split('\n'):
        if str(line).strip().lower().startswith('subdataset') \
          and str(line).strip().lower().find('_name') != -1:
            parts = line.split('=')
            yield (parts[0], parts[1])
# END - parse_hdf_subdatasets


#=============================================================================
def run_warp (source_file, output_file,
  min_x=None, min_y=None, max_x=None, max_y=None,
  pixel_size=None, projection=None, resample_method=None):
    '''
    Description:
      Executes the warping command on the specified source file
    '''

    cmd = build_warp_command (source_file, output_file, min_x, min_y, max_x,
        max_y, pixel_size, projection, resample_method)
    log ("Warping %s with %s" % (source_file, ' '.join(cmd)))
    output = subprocess.check_output (cmd)
    log (output)
# END - run_warp


#=============================================================================
def get_hdf_global_metadata(hdf_file):
    '''
    Description: TODO TODO TODO
    '''

    cmd = ['gdalinfo', hdf_file]
    output = subprocess.check_output (cmd)

    sb = StringIO()
    has_subdatasets = False
    for line in output.split('\n'):
        if str(line).strip().lower().startswith('metadata'):
            sb.write(line.strip())
            sb.write('\n')
            continue
        if str(line).strip().lower().startswith('subdatasets'):
            has_subdatasets = True
            break
        if str(line).strip().lower().startswith('corner'):
            break
        
    sb.flush()
    metadata = sb.getvalue()
    sb.close()

    return (metadata, has_subdatasets)
# END - get_hdf_global_metadata


#=============================================================================
def warp_science_products (parms):
    '''
    Description: TODO TODO TODO
    '''

    options = parms['options']
    sensor = options['sensor']

    if sensor not in valid_science_sensors:
        raise NotImplementedError ("Unsupported data sensor %s" % sensor)

    # Validate the parameters
    validate_parameters (parms)
    debug (parms)

    # Change to the working directory
    current_directory = os.curdir
    os.chdir(parms['work_directory'])

    # TODO - If the gap_mask directory is present for L7 data then we also
    #        need to figure out where and host to warp them??????

    try:
        # Include all HDF and TIF
        # TODO - Later we will do whatever is in the binary format + the TIF
        what_to_warp = glob.glob('*.hdf')
        what_to_warp += glob.glob('*.TIF')

        for file in what_to_warp:
            if file.endswith('hdf'):
                hdf_name = file.split('.hdf')[0]

                log ("Retrieving global HDF metadata")
                (metadata, has_subdatasets) = get_hdf_global_metadata(file)
                if metadata is not None and len(metadata) > 0:
                    metadata_filename = '%s.txt' % hdf_name

                    log ("Writing global metadata to %s" % metadata_filename)
                    fd = open(metadata_filename, 'w+')
                    fd.write(str(metadata))
                    fd.flush()
                    fd.close()

                if has_subdatasets:
                    for (sds_desc, sds_name) in parse_hdf_subdatasets(file):
                        sds_parts = sds_name.split(':')
                        output_filename = '%s-%s.tif' \
                            % (hdf_name, sds_parts[len(sds_parts) - 1])
                        run_warp(sds_name, output_filename)
                else:
                    output_filename = '%s.tif' % hdf_name
                    run_warp(file, output_filename)

                # Remove the HDF file, it is not needed anymore
                if os.path.exists(file):
                    os.unlink(file)

                # Remove the associated hdr file
                hdr_filename = '%s.hdr' % file
                if os.path.exists(hdr_filename):
                    os.unlink(hdr_filename)
            # END - HDF files
            else:
                # Assuming GeoTIFF
                output_filename = 'tmp-%s.tif' % file.split('.TIF')[0].lower()
                run_warp(file, output_filename)

                # Remove the TIF file, it is not needed anymore
                if os.path.exists(file):
                    os.unlink(file)

                # Rename the temp file back to the original name
                try:
                    os.rename(output_filename, file)
                except OSError, e:
                    log (str(e))
                    raise e
            # END - GeoTIFF
        # END - for each file
    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
# END - reproject_science_products

#=============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read parameters from the command line and build a JSON dictionary from
      them.  Pass the JSON dictionary to the process routine.
    '''

    # Build the command line argument parser
    parser = build_argument_parser() # TODO TODO TODO - Needs a lot of work

    # Parse the command line arguments
    args_dict = vars(parser.parse_args())

    # Build our JSON formatted input from the command line parameters
    orderid = args_dict.pop ('orderid')
    scene = args_dict.pop ('scene')
    options = {k : args_dict[k] for k in args_dict if args_dict[k] != None}

    # Build the JSON parameters dictionary
    json_parms['orderid'] = orderid
    json_parms['scene'] = scene
    json_parms['options'] = options

    try:
        # Call the main processing routine
        warp_science_products (parms)
    except Exception, e:
        log (str(e))
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

