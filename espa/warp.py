#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  See 'Description' under '__main__' for more details.
  Alters product extents, projections and pixel sizes.

History:
  Original Development (cdr_ecv.py) by David V. Hill, USGS/EROS
  Created Jan/2014 by Ron Dilley, USGS/EROS
    - Gutted the original implementation from cdr_ecv.py and placed it in this
      file.
'''

import os
import sys
import traceback
import glob
from cStringIO import StringIO
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
from espa_exception import ErrorCodes, ESPAException
import parameters
import util

# This contains the valid sensors which are supported
valid_landsat_sensors = ['LT', 'LE']
valid_modis_sensors = ['MODIS']
valid_science_sensors = valid_landsat_sensors + valid_modis_sensors

# These contain valid warping options
valid_resample_methods = ['near', 'bilinear', 'cubic', 'cubicspline', 'lanczos']
valid_pixel_units = ['meters', 'dd']
valid_projections = ['sinu', 'aea', 'utm', 'lonlat']
valid_utm = ['north', 'south']


#==============================================================================
def build_sinu_proj4_string(central_meridian, false_easting, false_northing):
    '''
    Description:
      Builds a proj.4 string for modis

    Example:
      +proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181
      +units=m +no_defs
    '''
    proj4_string = "'+proj=sinu +lon_0=%f +x_0=%f +y_0=%f +a=6371007.181" \
        " +b=6371007.181 +units=m +no_defs'" \
        % (central_meridian, false_easting, false_northing)

    return proj4_string
# END - build_sinu_proj4_string


#==============================================================================
def build_albers_proj4_string(std_parallel_1, std_parallel_2, origin_lat,
  central_meridian, false_easting, false_northing, datum):
    '''
    Description:
      Builds a proj.4 string for albers equal area

    Example:
      +proj=aea +lat_1=20 +lat_2=60 +lat_0=40 +lon_0=-96 +x_0=0 +y_0=0
      +ellps=GRS80 +datum=NAD83 +units=m +no_defs
    '''

    proj4_string = "'+proj=aea +lat_1=%f +lat_2=%f +lat_0=%f +lon_0=%f" \
        " +x_0=%f +y_0=%f +ellps=GRS80 +datum=%s +units=m +no_defs'" \
        % (std_parallel_1, std_parallel_2, origin_lat, central_meridian,
           false_easting, false_northing, datum)

    return proj4_string
# END - build_albers_proj4_string


#==============================================================================
def build_utm_proj4_string(utm_zone, utm_north_south):
    '''
    Description:
      Builds a proj.4 string for utm
    Example:
      +proj=utm +zone=60 +ellps=WGS84 +datum=WGS84 +units=m +no_defs
      +proj=utm +zone=39 +south +ellps=WGS72 +towgs84=0,0,1.9,0,0,0.814,-0.38
      +units=m +no_defs 
    '''

    proj4_string = ''
    if str(utm_north_south).lower() == 'north':
        proj4_string = "'+proj=utm +zone=%i +ellps=WGS84 +datum=WGS84" \
            " +units=m +no_defs'" % utm_zone
    elif str(utm_north_south).lower() == 'south':
        proj4_string = "'+proj=utm +zone=%i +south +ellps=WGS72" \
            " +towgs84=0,0,1.9,0,0,0.814,-0.38 +units=m +no_defs'" % utm_zone
    else:
        raise ValueError("Invalid utm_north_south argument[%s]" \
            " Argument must be one of 'north' or 'south'" % utm_north_south)

    return proj4_string
# END - build_utm_proj4_string


#==============================================================================
def build_geographic_proj4_string():
    '''
    Description:
      Builds a proj.4 string for geographic
    '''

    return "'+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'"
# END - build_geographic_proj4_string


#==============================================================================
def convert_target_projection_to_proj4 (parms):
    '''
    Description:
      Checks to see if the reproject parameter was set.  If set the
      target projection is validated against the implemented projections and
      depending on the projection, the correct proj4 parameters are returned.
    '''

    projection = None
    target_projection = None

    target_projection = parms['target_projection']

    if target_projection == "sinu":
        projection = \
            build_sinu_proj4_string(float(parms['central_meridian']),
                                    float(parms['false_easting']),
                                    float(parms['false_northing']))

    elif target_projection == "aea":
        projection = \
            build_albers_proj4_string(float(parms['std_parallel_1']),
                                      float(parms['std_parallel_2']),
                                      float(parms['origin_lat']),
                                      float(parms['central_meridian']),
                                      float(parms['false_easting']),
                                      float(parms['false_northing']),
                                      parms['datum'])

    elif target_projection == "utm":
        projection = \
            build_utm_proj4_string(int(parms['utm_zone']),
                                   parms['utm_north_south'])

    elif target_projection == "lonlat":
        projection = build_geographic_proj4_string()

    return projection
# END - convert_target_projection_to_proj4


#==============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser.
    '''

    # Create a command line argument parser
    description = "Alters product extents, projections and pixel sizes"
    parser = ArgumentParser (description=description)

    # Add parameters
    parameters.add_debug_parameter (parser)

    parameters.add_reprojection_parameters (parser, valid_projections,
        valid_utm, valid_pixel_units, valid_resample_methods)

    parameters.add_work_directory_parameter (parser)

    return parser
# END - build_argument_parser


#==============================================================================
def validate_parameters (parms):
    '''
    Description:
      Make sure all the parameters needed for this and called routines
      is available with the provided input parameters.
    '''

    parameters.validate_reprojection_parameters (parms, valid_projections,
        valid_utm, valid_pixel_units, valid_resample_methods)
# END - validate_parameters


#==============================================================================
def build_warp_command (source_file, output_file,
  min_x=None, min_y=None, max_x=None, max_y=None,
  pixel_size=None, projection=None, resample_method=None, no_data_value=None):
    '''
    Description:
      Builds the GDAL warp command to convert the data
    '''

    cmd = ['gdalwarp', '-wm', '2048', '-multi']

    # Subset the image using the specified extents
    if (min_x is not None) and (min_y is not None) \
      and (max_x is not None) and (max_y is not None):
        debug ("Image Extents: %s, %s, %s, %s" % (min_x, min_y, max_x, max_y))
        cmd += ['-te', min_x.strip(), min_y.strip(),
                max_x.strip(), max_y.strip()]

    # Resize the pixels
    if pixel_size is not None:
        cmd += ['-tr', pixel_size, pixel_size]

    # Reproject the data
    if projection is not None:
        cmd += ['-t_srs']
        cmd += [projection] # ***DO NOT*** split the projection string

    # Specify the resampling method
    if resample_method is not None:
        cmd += ['-r', resample_method]

    if no_data_value is not None:
        cmd += ['-srcnodata', no_data_value]
        cmd += ['-dstnodata', no_data_value]

    cmd += [source_file, output_file]

    return cmd
# END - build_warp_command


#==============================================================================
def parse_hdf_subdatasets (hdf_file):
    '''
    Description:
      Finds all the subdataset names in an hdf file
    '''

    cmd = ['gdalinfo', hdf_file]
    cmd = ' '.join(cmd)
    output = util.execute_cmd (cmd)
    name = ''
    description = ''
    for line in output.split('\n'):
        line_lower = line.strip().lower()

        # logic heavily based on the output order from gdalinfo
        if line_lower.startswith('subdataset') \
          and line_lower.find('_name') != -1:
            parts = line.split('=')
            name = parts[1]
        if line_lower.startswith('subdataset') \
          and line_lower.find('_desc') != -1:
            parts = line.split('=')
            description = parts[1]
            yield (description, name)
# END - parse_hdf_subdatasets


#==============================================================================
def get_no_data_value (hdf_name):
    cmd = ['gdalinfo', hdf_name]
    cmd = ' '.join(cmd)
    output = util.execute_cmd (cmd)

    no_data_value = None
    for line in output.split('\n'):
        line_lower = line.strip().lower()

        if line_lower.startswith('nodata value'):
            no_data_value = line_lower.split('=')[1] # take second element

    return no_data_value
# END - get_no_data_value


#==============================================================================
def run_warp (source_file, output_file,
  min_x=None, min_y=None, max_x=None, max_y=None,
  pixel_size=None, projection=None, resample_method=None, no_data_value=None):
    '''
    Description:
      Executes the warping command on the specified source file
    '''

    cmd = build_warp_command (source_file, output_file, min_x, min_y, max_x,
        max_y, pixel_size, projection, resample_method, no_data_value)
    cmd = ' '.join(cmd)
    log ("Warping %s with %s" % (source_file, cmd))
    output = util.execute_cmd (cmd)
    log (output)
# END - run_warp


#==============================================================================
def get_hdf_global_metadata(hdf_file):
    '''
    Description:
        Extract the metadata information from the HDF formatted file
    '''

    cmd = ['gdalinfo', hdf_file]
    cmd = ' '.join(cmd)
    output = util.execute_cmd (cmd)

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


#==============================================================================
def warp_science_products (parms):
    '''
    Description:
      Warp each science product to the parameters specified in the parms
    '''

    # Validate the parameters
    validate_parameters (parms)
    debug (parms)

    if parms['projection'] is not None:
        # Use the provided proj.4 projection information
        projection = parms['projection']
    elif parms['reproject']:
        # Verify and create proj.4 projection information
        projection = convert_target_projection_to_proj4 (parms)
    else:
        projection = None

    # Change to the working directory
    current_directory = os.getcwd()
    os.chdir(parms['work_directory'])

    min_x = parms['minx']
    min_y = parms['miny']
    max_x = parms['maxx']
    max_y = parms['maxy']
    pixel_size = parms['pixel_size']
    resample_method = parms['resample_method']

    try:
        # Include all HDF and TIF
        what_to_warp = glob.glob('*.hdf')
        what_to_warp += glob.glob('*.TIF')
        what_to_warp += glob.glob('*.tif') # capture the browse

        for file in what_to_warp:
            log ("Processing %s" % file)
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
                        # Split the name into parts to extract the subdata name
                        sds_parts = sds_name.split(':')
                        subdata_name = sds_parts[len(sds_parts) - 1]
                        no_data_value = get_no_data_value (sds_name)

                        # Split the description into part to extract the string
                        # which allows for determining the correct gdal data
                        # data type, allowing specifying the correct no-data
                        # value
                        sds_parts = sds_desc.split('(')
                        sds_parts = sds_parts[len(sds_parts) - 1].split(')')
                        hdf_type = sds_parts[0]

                        log ("Processing Subdataset %s" % sds_name)

                        output_filename = '%s-%s.tif' % (hdf_name, subdata_name)
                        run_warp(sds_name, output_filename,
                            min_x, min_y, max_x, max_y,
                            pixel_size, projection, resample_method,
                            no_data_value)
                else:
                    output_filename = '%s.tif' % hdf_name

                    no_data_value = get_no_data_value (file)
                    run_warp(file, output_filename,
                        min_x, min_y, max_x, max_y,
                        pixel_size, projection, resample_method, no_data_value)

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
                if "TIF" in file:
                    output_filename = 'tmp-%s.tif' \
                        % file.split('.TIF')[0].lower()
                    no_data_value = '0' # Assuming Landsat data
                else:
                    output_filename = 'tmp-%s' % file.lower()
                    no_data_value = get_no_data_value (file)

                run_warp(file, output_filename,
                    min_x, min_y, max_x, max_y,
                    pixel_size, projection, resample_method, no_data_value)

                # Remove the TIF file, it is not needed anymore
                if os.path.exists(file):
                    os.unlink(file)

                # Rename the temp file back to the original name
                os.rename(output_filename, file)
            # END - GeoTIFF
        # END - for each file
    except Exception, e:
        raise ESPAException (ErrorCodes.warping, str(e)), \
            None, sys.exc_info()[2]
    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
# END - reproject_science_products


#==============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read parameters from the command line and build a JSON dictionary from
      them.  Pass the JSON dictionary to the process routine.
    '''

    # Build the command line argument parser
    parser = build_argument_parser()

    # Parse the command line arguments
    args = parser.parse_args()
    args_dict = vars(parser.parse_args())

    # Setup debug
    set_debug (args.debug)

    # Build our JSON formatted input from the command line parameters
    options = {k : args_dict[k] for k in args_dict if args_dict[k] != None}

    try:
        # Call the main processing routine
        warp_science_products (options)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

