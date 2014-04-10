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
from osgeo import gdal

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug
import metadata_api

# local objects and methods
import espa_exception as ee
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


#=============================================================================
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

    proj4_string = "'+proj=aea +lat_1=%f +lat_2=%f +lat_0=%f +lon_0=%f" \
        " +x_0=%f +y_0=%f +ellps=GRS80 +datum=%s +units=m +no_defs'" \
        % (std_parallel_1, std_parallel_2, origin_lat, central_meridian,
           false_easting, false_northing, datum)

    return proj4_string
# END - build_albers_proj4_string


#=============================================================================
def build_utm_proj4_string(utm_zone, utm_north_south):
    '''
    Description:
      Builds a proj.4 string for utm

    Examples:
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


# TODO TODO TODO - Fix when the parameters are finalized
def build_ps_proj4_string(lat_ts, lon_pole,
  false_easting, false_northing, datum, north_south):
    '''
    Description:
      Builds a proj.4 string for polar stereographic

    Examples:
      +proj=stere +lat_ts=30 +lat_0=90 +lon_0=30 +k_0=1.0 +x_0=0 +y_0=0

      +proj=stere +lat_ts=30 +lat_0=-90 +lon_0=30 +k_0=1.0 +x_0=0 +y_0=0
    '''

    lat_o = ''
    if str(north_south).lower() == 'north':
        lat_o = '+lat_o=%f' % 90
    elif str(north_south).lower() == 'south':
        lat_o = '+lat_o=%f' % -90
    else:
        raise ValueError("Invalid north_south argument[%s]" \
            " Argument must be one of 'north' or 'south'" % utm_north_south)

# TODO TODO TODO - NEEDS TESTING MAY NOT BE CORRECT - ASSUMPTIONS MADE
    proj4_string = '+proj=stere'
    proj4_string += ' +lat_ts=%f %s +lon_0=%f +k_0=1.0 +x_0=%f +y_0=%f' \
        % (lat_ts, lon_pole, false_easting, false_northing)
    proj4_string += ' +datum=%s +units=m +no_defs' % datum

    return proj4_string
# END - build_ps_proj4_string


#=============================================================================
def build_geographic_proj4_string():
    '''
    Description:
      Builds a proj.4 string for geographic
    '''

    return "'+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs'"
# END - build_geographic_proj4_string


#=============================================================================
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

    elif target_projection == "ps":
# TODO TODO TODO - Fix when the parameters are finalized
        projection = build_ps_proj4_string(float(parms['lat_ts']),
                                           float(parms['lon_pole']),
                                           float(parms['false_easting']),
                                           float(parms['false_northing']),
                                           parms['datum'],
                                           parms['north_south']):

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
    description = "Alters product extents, projections and pixel sizes"
    parser = ArgumentParser (description=description)

    # Add parameters
    parameters.add_debug_parameter (parser)

    parameters.add_reprojection_parameters (parser, valid_projections,
        valid_utm, valid_pixel_units, valid_resample_methods)

    parameters.add_work_directory_parameter (parser)

    return parser
# END - build_argument_parser


#=============================================================================
def validate_parameters (parms):
    '''
    Description:
      Make sure all the parameters needed for this and called routines
      is available with the provided input parameters.
    '''

    parameters.validate_reprojection_parameters (parms, valid_projections,
        valid_utm, valid_pixel_units, valid_resample_methods)
# END - validate_parameters


#=============================================================================
def build_warp_command (source_file, output_file, output_format='envi',
  min_x=None, min_y=None, max_x=None, max_y=None,
  pixel_size=None, projection=None, resample_method=None, no_data_value=None):
    '''
    Description:
      Builds the GDAL warp command to convert the data
    '''

    cmd = ['gdalwarp', '-wm', '2048', '-multi', '-of', output_format]

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


#=============================================================================
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


#=============================================================================
def get_no_data_value (filename):
    cmd = ['gdalinfo', filename]
    cmd = ' '.join(cmd)
    output = util.execute_cmd (cmd)

    no_data_value = None
    for line in output.split('\n'):
        line_lower = line.strip().lower()

        if line_lower.startswith('nodata value'):
            no_data_value = line_lower.split('=')[1] # take second element

    return no_data_value
# END - get_no_data_value


#=============================================================================
def run_warp (source_file, output_file, output_format='envi',
  min_x=None, min_y=None, max_x=None, max_y=None,
  pixel_size=None, projection=None, resample_method=None, no_data_value=None):
    '''
    Description:
      Executes the warping command on the specified source file
    '''

    cmd = build_warp_command (source_file, output_file, output_format,
        min_x, min_y, max_x, max_y, pixel_size, projection,
        resample_method, no_data_value)
    debug (cmd)
    cmd = ' '.join(cmd)

    log ("Warping %s with %s" % (source_file, cmd))
    output = util.execute_cmd (cmd)
    log (output)
# END - run_warp


#=============================================================================
def get_hdf_global_metadata(hdf_file):
    '''
    Description:
        Extract the metadata information from the HDF formatted file

    Note: Works with Ledaps and Modis generated HDF files
    '''

    cmd = ['gdalinfo', hdf_file]
    cmd = ' '.join(cmd)
    output = util.execute_cmd (cmd)

    sb = StringIO()
    has_metadata = False
    for line in output.split('\n'):
        if str(line).strip().lower().startswith('metadata'):
            has_metadata = True
        if str(line).strip().lower().startswith('subdatasets'):
            break
        if str(line).strip().lower().startswith('corner'):
            break
        if has_metadata:
            sb.write(line.strip())
            sb.write('\n')

    sb.flush()
    metadata = sb.getvalue()
    sb.close()

    return metadata
# END - get_hdf_global_metadata


#=============================================================================
def hdf_has_subdatasets (hdf_file):
    '''
    Description:
        Determine if the HDF file has subdatasets
    '''

    cmd = ['gdalinfo', hdf_file]
    cmd = ' '.join(cmd)
    output = util.execute_cmd (cmd)

    for line in output.split('\n'):
        if str(line).strip().lower().startswith('subdatasets'):
            return True

    return False
# END - hdf_has_subdatasets


#=============================================================================
def convert_hdf_to_gtiff (hdf_file):
    '''
    Description:
        Convert HDF formatted data to GeoTIFF
    '''

    hdf_name = hdf_file.split('.hdf')[0]
    output_format = 'gtiff'

    log ("Retrieving global HDF metadata")
    metadata = get_hdf_global_metadata(hdf_file)
    if metadata is not None and len(metadata) > 0:
        metadata_filename = '%s-global_metadata.txt' % hdf_name

        log ("Writing global metadata to %s" % metadata_filename)
        fd = open(metadata_filename, 'w+')
        fd.write(str(metadata))
        fd.flush()
        fd.close()

    # Extract the subdatasets into individual GeoTIFF files
    if hdf_has_subdatasets (hdf_file):
        for (sds_desc, sds_name) in parse_hdf_subdatasets(hdf_file):
            # Split the name into parts to extract the subdata name
            sds_parts = sds_name.split(':')
            subdata_name = sds_parts[len(sds_parts) - 1]
            # Quote the sds name due to possible spaces
            # Must be single because have double quotes in sds name
            quoted_sds_name = "'" + sds_name + "'"
            no_data_value = get_no_data_value (quoted_sds_name)

            # Split the description into part to extract the string
            # which allows for determining the correct gdal data
            # data type, allowing specifying the correct no-data
            # value
            sds_parts = sds_desc.split('(')
            sds_parts = sds_parts[len(sds_parts) - 1].split(')')
            hdf_type = sds_parts[0]

            log ("Processing Subdataset %s" % quoted_sds_name)

            # Remove spaces from the subdataset name for the
            # final output name
            subdata_name = subdata_name.replace(' ', '_')
            output_filename = '%s-%s.tif' % (hdf_name, subdata_name)

            run_warp(quoted_sds_name, output_filename, output_format,
                #min_x, min_y, max_x, max_y,
                None, None, None, None,
                #pixel_size, projection, resample_method,
                None, None, 'near',
                no_data_value)

    # We only have the one dataset in the HDF file
    else:
        output_filename = '%s.tif' % hdf_name

        no_data_value = get_no_data_value (hdf_file)
        run_warp(file, output_filename, output_format,
            min_x, min_y, max_x, max_y,
            pixel_size, projection, resample_method, no_data_value)

    # Remove the HDF file, it is not needed anymore
    if os.path.exists(hdf_file):
        os.unlink(hdf_file)

    # Remove the associated hdr file
    hdr_filename = '%s.hdr' % hdf_file
    if os.path.exists(hdr_filename):
        os.unlink(hdr_filename)
# END - convert_hdf_to_gtiff


#=============================================================================
def warp_espa_data (parms, xml_filename=None):
    '''
    Description:
      Warp each espa science product to the parameters specified in the parms
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
    pixel_size_units = parms['pixel_size_units']
    resample_method = parms['resample_method']

    try:
        xml = metadata_api.parse (xml_filename, silence=True)
        bands = xml.get_bands()
        global_metadata = xml.get_global_metadata()
        # These will be poulated with the last bands information
        map_info_str = None
        x_pixel_size = None
        y_pixel_size = None

        # Process through the bands in the XML file
        for band in bands.band:
            img_filename = band.get_file_name()
            hdr_filename = img_filename.replace('.img', '.hdr')
            log ("Processing %s" % img_filename)

            # Open the image to read the no data value out since the internal
            # ENVI driver for GDAL does not output it, even if it is known
            ds = gdal.Open (img_filename)
            if ds is None:
                raise RuntimeError ("GDAL failed to open (%s)" % img_filename)

            try:
                ds_band = ds.GetRasterBand (1)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.warping, str(e)), \
                    None, sys.exc_info()[2]

            # TODO - We don't process any floating point data types.... Yet
            # Save the no data value since gdalwarp does not write it out when
            # using the ENVI format
            no_data_value = ds_band.GetNoDataValue()
            if no_data_value is None:
                raise RuntimeError ("no_data_value = None")
            else:
                # Convert to an integer then string
                no_data_value = str(int(no_data_value))

            del (ds_band)
            del (ds)

            tmp_img_filename = 'tmp-%s' % img_filename
            tmp_hdr_filename = 'tmp-%s' % hdr_filename

            run_warp(img_filename, tmp_img_filename, 'envi',
                min_x, min_y, max_x, max_y,
                pixel_size, projection, resample_method, no_data_value)

            # Get the lines and samples for the newly projected band
            ds = gdal.Open (tmp_img_filename)
            if ds is None:
                msg = "GDAL failed to open (%s)" % tmp_img_filename
                raise RuntimeError (msg)

            try:
                ds_band = ds.GetRasterBand (1)
                ds_geo_transform = ds.GetGeoTransform()
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.warping, str(e)), \
                    None, sys.exc_info()[2]

            number_of_lines = ds_band.YSize
            number_of_samples = ds_band.XSize
            # Need to abs these because they are coming from the transform,
            # which may becorrect for the transform,
            # but not how us humans understand it
            x_pixel_size =  abs(ds_geo_transform[1])
            y_pixel_size =  abs(ds_geo_transform[5])

            del (ds_geo_transform)
            del (ds_band)
            del (ds)

            # Update the tmp ENVI header with our own values for some fields
            sb = StringIO()
            fd = open(tmp_hdr_filename, 'r')
            while 1:
                line = fd.readline()
                if not line:
                    break
                if line.startswith('data ignore value') \
                  or line.startswith('description'):
                    dummy = 'Nothing'
                else:
                    sb.write(line)

                if line.startswith('description'):
                    # This may be on multiple lines so read lines until found
                    if not line.strip().endswith('}'):
                        while 1:
                            next_line = fd.readline()
                            if not next_line or next_line.strip().endswith('}'):
                                break
                    sb.write('description = {ESPA-generated file}\n')
                elif line.startswith('data type'):
                    sb.write('data ignore value = %s\n' % no_data_value)
                elif line.startswith('map info'):
                    map_info_str = line

            fd.close()
            sb.flush()

            # Do the actual update here
            fd = open(tmp_hdr_filename, 'w')
            fd.write(sb.getvalue())
            fd.flush()
            fd.close()

            # Remove the original files, they are replaced in following code
            if os.path.exists(img_filename):
                os.unlink(img_filename)
            if os.path.exists(hdr_filename):
                os.unlink(hdr_filename)

            # Rename the temps file back to the original name
            os.rename(tmp_img_filename, img_filename)
            os.rename(tmp_hdr_filename, hdr_filename)

            # Update the band information in the XML file
            band.set_nlines (number_of_lines)
            band.set_nsamps (number_of_lines)
            band_pixel_size = band.get_pixel_size()
            band_pixel_size.set_x (x_pixel_size)
            band_pixel_size.set_y (y_pixel_size)
            # Use the units from the order request options
            band_pixel_size.set_units = pixel_size_units
        # END for each band in the XML file

        # TODO TODO TODO - Update the global metadata with the map info
        # All the bands have the same projection at this point so we can use
        # use the map information from the last band processed
        map_info_list = map_info_str.split('{')[1].split('}')[0].split(',')
#if map_info_list[0].strip() == 'UTM':
#    map_info2['projection'] = map_info_list[0].strip()
#    map_info2['pixel_x'] = map_info_list[1].strip()
#    map_info2['pixel_y'] = map_info_list[2].strip()
#    map_info2['false_easting'] = map_info_list[3].strip()
#    map_info2['false_northing'] = map_info_list[4].strip()
#    map_info2['pixel_size_x'] = map_info_list[5].strip()
#    map_info2['pixel_size_y'] = map_info_list[6].strip()
#    map_info2['zone'] = map_info_list[7].strip()
#    map_info2['northsouth'] = map_info_list[7].strip()
#    if map_info_list[9] is not None:
#        map_info2['datum'] = map_info_list[9].strip()

        # Write out a new XML file after validation
        tmp_xml_filename = 'tmp-%s' % xml_filename
        fd = open(tmp_xml_filename, 'w')
        # Call the export with validation and specifing the namespace/schema
        # TODO TODO TODO - This doesn't fail when it should
        metadata_api.export(fd, xml,
            xmlns="http://espa.cr.usgs.gov/v1.0",
            xmlns_xsi="http://www.w3.org/2001/XMLSchema-instance",
            schema_uri="http://espa.cr.usgs.gov/static/schema/espa_internal_metadata_v1_0.xsd")
        fd.close()

        # Remove the original
        if os.path.exists(xml_filename):
            os.unlink(xml_filename)

        # Rename the temp file back to the original name
        os.rename(tmp_xml_filename, xml_filename)

        del (xml)

    except Exception, e:
        raise ee.ESPAException (ee.ErrorCodes.warping, str(e)), \
            None, sys.exc_info()[2]
    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
# END - warp_espa_data


#=============================================================================
def warp_science_products (parms, xml_filename=None):
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
        # First convert any HDF to GeoTIFF
        what_to_convert = glob.glob('*.hdf')
        for filename in what_to_convert:
            log ("Converting %s to GeoTIFF" % filename)
            convert_hdf_to_gtiff (filename)

        # Now warp the GeoTIFF files
        what_to_warp = glob.glob('*.TIF')
        what_to_warp += glob.glob('*.tif') # capture the browse
        output_format = 'gtiff'
        for filename in what_to_warp:
            log ("Processing %s" % filename)

            if "TIF" in filename:
                output_filename = 'tmp-%s.tif' \
                    % filename.split('.TIF')[0].lower()
                no_data_value = '0' # Assuming Landsat data
            else:
                output_filename = 'tmp-%s' % filename.lower()
                no_data_value = get_no_data_value (filename)

            run_warp(filename, output_filename, output_format,
                min_x, min_y, max_x, max_y,
                pixel_size, projection, resample_method, no_data_value)

            # Remove the original file, it is not needed anymore
            if os.path.exists(filename):
                os.unlink(filename)

            # Rename the temp file back to the original name
            os.rename(output_filename, filename)
        # END - for each file

        # Now warp the ESPA files
        if xml_filename != None:
            warp_espa_data(parms, xml_filename)

    except Exception, e:
        raise ee.ESPAException (ee.ErrorCodes.warping, str(e)), \
            None, sys.exc_info()[2]
    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
# END - warp_science_products


#=============================================================================
def reformat (metadata_filename, work_directory, input_format, output_format):
    '''
    Description:
      Re-format the bands to the specified format using our raw binary tools
      or gdal, whichever is appropriate for the task.

      Input espa:
          Output Formats: envi(espa), gtiff, and hdf
    '''

    # Don't do anything if they match
    if input_format == output_format:
        return

    # Change to the working directory
    current_directory = os.getcwd()
    os.chdir (work_directory)

    try:
        # Convert from our internal ESPA/ENVI format to GeoTIFF
        if input_format == 'envi' and output_format == 'gtiff':
            gtiff_name = metadata_filename.rstrip ('.xml')
            # Call with deletion of source files
            cmd = ['convert_espa_to_gtif', '--del_src_files',
                   '--xml', metadata_filename,
                   '--gtif', gtiff_name]
            cmd = ' '.join (cmd)

            # Turn GDAL PAM off
            os.environ['GDAL_PAM_ENABLED'] = 'NO'

            output = ''
            try:
                output = util.execute_cmd (cmd)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.reformat, str(e)), \
                    None, sys.exc_info()[2]
            if len(output) > 0:
                log (output)

            # Remove the environment variable
            del os.environ['GDAL_PAM_ENABLED']

            world_files = glob.glob ('*.tfw')
            cmd = ['rm', '-f'] + world_files
            cmd = ' '.join (cmd)

            log ('REMOVING WORLD FILES COMMAND:' + cmd)
            output = ''
            try:
                output = util.execute_cmd (cmd)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.reformat, str(e)), \
                    None, sys.exc_info()[2]
            if len(output) > 0:
                log (output)

        # Convert from our internal ESPA/ENVI format to HDF
# TODO TODO TODO - Not Tested
        elif input_format == 'envi' and output_format == 'hdf':
            # convert_espa_to_hdf
            hdf_name = metadata_filename.replace ('.xml', '.hdf')
            # Call with deletion of source files
            cmd = ['convert_espa_to_hdf', '--del_src_files',
                   '--xml', metadata_filename,
                   '--hdf', hdf_name]
            cmd = ' '.join (cmd)
            output = util.execute_cmd (cmd)
            if len(output) > 0:
                log (output)

        # Requested conversion not implemented
        else:
            raise ValueError ("Unsupported reformat combination (%s, %s)" \
                % (input_format, output_format))

    except Exception, e:
        raise ee.ESPAException (ee.ErrorCodes.reformat, str(e)), \
            None, sys.exc_info()[2]
    finally:
        # Change back to the previous directory
        os.chdir (current_directory)
# END - reformat


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

