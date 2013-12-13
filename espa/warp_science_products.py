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

# These contain valid warping options
valid_resample_methods = ['near', 'bilinear', 'cubic', 'cubicspline', 'lanczos']
valid_pixel_units = ['meters', 'dd']
valid_projections = ['sinu', 'aea', 'utm', 'lonlat']


#=============================================================================
def build_sinu_proj4_string(central_meridian, false_easting, false_northing):
    '''
    Description:
      Builds a proj.4 string for modis

    Example:
      +proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181
      +units=m +no_defs
    '''
    proj4_string = "+proj=sinu +lon_0=%f +x_0=%f +y_0=%f +a=6371007.181" \
        " +b=6371007.181 +units=m +no_defs" \
        % (central_meridian, false_easting, false_northing)

    return proj4_string
# END - build_sinu_proj4_string


#=============================================================================
def build_albers_proj4_string(std_parallel_1, std_parallel_2, origin_lat,
  central_meridian, false_easting, false_northing, datum):
    '''
    Description:
      Builds a proj.4 string for albers equal area

    Example:
      +proj=aea +lat_1=20 +lat_2=60 +lat_0=40 +lon_0=-96 +x_0=0 +y_0=0
      +ellps=GRS80 +datum=NAD83 +units=m +no_defs
    '''

    proj4_string = "+proj=aea +lat_1=%f +lat_2=%f +lat_0=%f +lon_0=%f" \
        " +x_0=%f +y_0=%f +ellps=GRS80 +datum=%s +units=m +no_defs" \
        % (std_parallel_1, std_parallel_2, origin_lat, central_meridian,
           false_easting, false_northing, datum)

    return proj4_string
# END - build_albers_proj4_string


#=============================================================================
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
        proj4_string = "+proj=utm +zone=%i +ellps=WGS84 +datum=WGS84" \
            " +units=m +no_defs" % utm_zone
    elif str(utm_north_south).lower() == 'south':
        proj4_string = "+proj=utm +zone=%i +south +ellps=WGS72" \
            " +towgs84=0,0,1.9,0,0,0.814,-0.38 +units=m +no_defs" % utm_zone
    else:
        raise ValueError("Invalid utm_north_south argument[%s]" \
            " Argument must be one of 'north' or 'south'" % utm_north_south)

    return proj4_string
# END - build_utm_proj4_string


#=============================================================================
def build_geographic_proj4_string():
    '''
    Description:
      Builds a proj.4 string for geographic
    '''

    return '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'
# END - build_geographic_proj4_string


#=============================================================================
def convert_target_projection_to_proj4 (parms):
    '''
    Description:
      Checks to see if the reproject parameter was set.  If set the
      target projection is validated against the implemented projections and
      depending on the projection, the correct proj4 parameters are returned.
    '''

    options = parms['options']
    projection = None
    target_projection = None

    if parameters.test_for_parameter (options, 'target_projection'):
        target_projection = options['target_projection'].lower()
    else:
        raise RuntimeError ("Missing target_projection option")

    if target_projection not in valid_projections:
        raise NotImplementedError ("Projection %s is not implemented" % \
            target_projection)

    if target_projection == "sinu":
        if not parameters.test_for_parameter (options, 'central_meridian'):
            raise RuntimeError ("Missing central_meridian option")
        if not parameters.test_for_parameter (options, 'false_easting'):
            raise RuntimeError ("Missing false_easting option")
        if not parameters.test_for_parameter (options, 'false_northing'):
            raise RuntimeError ("Missing false_northing option")

        projection = \
            build_sinu_proj4_string(float(options['central_meridian']),
                                    float(options['false_easting']),
                                    float(options['false_northing']))

    elif target_projection == "aea":
        if not parameters.test_for_parameter (options, 'std_parallel_1'):
            raise RuntimeError ("Missing std_parallel_1 option")
        if not parameters.test_for_parameter (options, 'std_parallel_2'):
            raise RuntimeError ("Missing std_parallel_2 option")
        if not parameters.test_for_parameter (options, 'origin_lat'):
            raise RuntimeError ("Missing origin_lat option")
        if not parameters.test_for_parameter (options, 'central_meridian'):
            raise RuntimeError ("Missing central_meridian option")
        if not parameters.test_for_parameter (options, 'false_easting'):
            raise RuntimeError ("Missing false_easting option")
        if not parameters.test_for_parameter (options, 'false_northing'):
            raise RuntimeError ("Missing false_northing option")

        projection = \
            build_albers_proj4_string(float(options['std_parallel_1']),
                                      float(options['std_parallel_2']),
                                      float(options['origin_lat']),
                                      float(options['central_meridian']),
                                      float(options['false_easting']),
                                      float(options['false_northing']),
                                      options['datum'])

    elif target_projection == "utm":
        if not parameters.test_for_parameter (options, 'utm_zone'):
            raise RuntimeError ("Missing utm_zone option")
        if not parameters.test_for_parameter (options, 'utm_north_south'):
            raise RuntimeError ("Missing utm_north_south option")

        projection = \
            build_utm_proj4_string(int(options['utm_zone']),
                                   options['utm_north_south'])

    elif target_projection == "lonlat":
        projection = build_geographic_proj4_string()

    return projection
# END - convert_target_projection_to_proj4


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

    parser.add_argument("--minx",
        action="store", dest="minx",
        help="minimum x image exntent")

    parser.add_argument("--miny",
        action="store", dest="miny",
        help="minimum y image exntent")

    parser.add_argument("--maxx",
        action="store", dest="maxx",
        help="maximum x image exntent")

    parser.add_argument("--maxy",
        action="store", dest="maxy",
        help="maximum y image exntent")

    parser.add_argument("--projection",
        action="store", dest="projection",
        help="proj.4 string for desired output projection")

    parser.add_argument("--pixel_units",
        action="store", dest="pixel_units", default='meters',
        choices=valid_pixel_units,
        help="one of %s" % ", ".join(valid_pixel_units))

    parser.add_argument("--pixel_size",
        action="store", dest="pixel_size", default=30.0,
        help="size of the pixels")

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

    if parameters.test_for_parameter (options, 'resample_method'):
        if options['resample_method'] not in valid_resample_methods:
            raise NotImplementedError ("Unsupported resample_method [%s]" % \
                options['resample_method'])

    if parameters.test_for_parameter (options, 'pixel_units'):
        if options['pixel_units'] not in valid_pixel_units:
            raise NotImplementedError ("Unsupported pixel_units [%s]" % \
                options['pixel_units'])

    if parameters.test_for_parameter (options, 'reproject'):
        # Verify and create proj.4 reprojection information
        options['projection'] = convert_target_projection_to_proj4 (parms)

    # Fix the pixel size and units if needed
    if parameters.test_for_parameter (options, 'resize'):
        if not parameters.test_for_parameter (options, 'pixel_size'):
            raise RuntimeError ("Missing pixel_size option")
        if not parameters.test_for_parameter (options, 'pixel_units'):
            raise RuntimeError ("Missing pixel_units option")
    elif parameters.test_for_parameter (options, 'reproject') \
      or parameters.test_for_parameter (options, 'image_extents'):
        # Sombody asked for reproject or extents, but didn't specify a pixel
        # size
        # Default to 30 meters of dd equivalent
        # Everything will default to 30 meters except if they chose geographic
        # projection, which will default to dd equivalent
        options['pixel_size'] = 30.0
        options['pixel_units'] = 'meters'
        if parameters.test_for_parameter (options, 'target_projection'):
            if str(options['target_projection']).lower() == 'lonlat':
                options['pixel_size'] = .0002695
                options['pixel_units'] = 'dd'

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
        cmd += ['-t_srs']
        cmd += [projection] # ***DO NOT*** split the projection string

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
    Description:
        Extract the metadata information from the HDF formatted file
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
    Description:
      Warp each science product to the parameters specified in the options
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

    projection = options['projection']
    min_x = options['minx']
    min_y = options['miny']
    max_x = options['maxx']
    max_y = options['maxy'],
    pixel_size = options['pixel_size']
    resample_method = options['resample_method']

    # TODO - If the gap_mask directory is present for L7 data then we also
    #        need to figure out where and how to warp them ????
    #        ???? WE ARE NOT DOING THIS TODAY, SHOULD WE ????

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
                        run_warp(sds_name, output_filename,
                            min_x, min_y, max_x, max_y,
                            pixel_size, projection, resample_method)
                else:
                    output_filename = '%s.tif' % hdf_name
                    run_warp(file, output_filename,
                        min_x, min_y, max_x, max_y,
                        pixel_size, projection, resample_method)

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
                run_warp(file, output_filename,
                    min_x, min_y, max_x, max_y,
                    pixel_size, projection, resample_method)

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
    parser = build_argument_parser()

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

