#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Build science products from Landsat L4TM, L5TM, and L7ETM+ data.

History:
  Original Development (cdr_ecv.py) by David V. Hill, USGS/EROS
  Created Jan/2014 by Ron Dilley, USGS/EROS
    - Gutted the original implementation from cdr_ecv.py and placed it in this
      file.
'''

import os
import sys
import glob
import traceback
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
import espa_exception as ee
import parameters
import util
import metadata
import metadata_api
import solr
# We do not offer browse products for the time being.
#import browse


# Default values
default_browse_resolution = 50
default_solr_collection_name = 'DEFAULT_COLLECTION'


# Define all of the non-product files that need to be removed before product
# generation
non_product_files = [
    'lndsr.*.txt',
    'lndcal.*.txt',
    'LogReport*',
    'README*'
    '*_dem.img'
]

# Define L1T source files that may need to be removed before product generation
l1t_source_files = [
    '*gap_mask*'
]

# Define L1T source metadata files that may need to be removed before product
# generation
l1t_source_metadata_files = [
    '*MTL*',
    '*VER*',
    '*GCP*'
]

order_to_product_mapping = {
    'include_sourcefile': 'L1T',
    'include_sr': 'sr_refl',
    'include_sr_toa': 'toa_refl',
    'include_sr_thermal': 'toa_bt',
    'include_cfmask': 'cfmask'
}


#=============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser.
    '''

    # Create a command line argument parser
    desacription = "Build science products from Landsat L4TM, L5TM," \
        " and L7ETM+ data"
    parser = ArgumentParser(description=description)

    # Parameters
    parameters.add_debug_parameter (parser)

    parameters.add_scene_parameter (parser)

    parameters.add_work_directory_parameter (parser)

    parameters.add_data_type_parameter (parser, parameters.valid_data_types)

    parameters.add_science_product_parameters (parser)

    return parser
# END - build_argument_parser


#=============================================================================
def validate_landsat_parameters (parms):
    '''
    Description:
      Make sure all the parameter options needed for this and called routines
      is available with the provided input parameters.
    '''

    # Test for presence of top-level parameters
    keys = ['scene', 'options']
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
    keys = ['include_sr', 'include_sr_toa', 'include_sr_thermal',
            'include_sr_browse', 'include_sr_nbr', 'include_sr_nbr2',
            'include_sr_ndvi', 'include_sr_ndmi', 'include_sr_savi',
            'include_sr_msavi', 'include_sr_evi', 'include_snow_covered_area',
            'include_surface_water_extent', 'include_solr_index']

    for key in keys:
        if not parameters.test_for_parameter (options, key):
            options[key] = False

    # Determine if browse was requested and specify the default resolution if
    # a resolution was not specified
    if options['include_sr_browse']:
        if not parameters.test_for_parameter (options, 'browse_resolution'):
            options['browse_resolution'] = default_browse_resolution

    # Determine if SOLR was requested and specify the default collection name
    # if a collection name was not specified
    if options['include_solr_index']:
        if not parameters.test_for_parameter (options, 'collection_name'):
            options['collection_name'] = default_solr_collection_name
# END - validate_landsat_parameters


def remove_products (xml_filename, products_to_remove=None):
    '''
    Description:
      Remove the specified products from the XML file.  The file is read into
      memory, processed, and written back out with out the specified products.
    '''

    if products_to_remove != None:
        espa_xml = metadata_api.parse (xml_filename, silence=True)
        bands = espa_xml.get_bands()

        file_names = []

        # Remove them from the file system first
        for band in bands.band:
            if band.product in products_to_remove:
                file_name = band.file_name.rsplit ('.')[0]
                file_names += glob.glob ('%s*' % file_name)

        # Only remove files if we found some
        if len(file_names) > 0:

            cmd = ['rm', '-rf'] + file_names
            cmd = ' '.join(cmd)
            log ('REMOVING INTERMEDIAT PRODUCTS NOT REQUESTED COMMAND:' + cmd)

            try:
                output = util.execute_cmd (cmd)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.remove_products, str(e)), \
                    None, sys.exc_info()[2]
            finally:
                log (output)

            # Remove them from the XML by creating a new list of all the others
            bands.band[:] = [band for band in bands.band if band.product not in products_to_remove]

            try:
                # Export the file with validation
                xml_fd = open(xml_filename, 'w')
                # Export to the file and specify the namespace/schema
                metadata_api.export(xml_fd, espa_xml,
                    xmlns="http://espa.cr.usgs.gov/v1.0",
                    xmlns_xsi="http://www.w3.org/2001/XMLSchema-instance",
                    schema_uri="http://espa.cr.usgs.gov/static/schema/espa_internal_metadata_v1_0.xsd")
                xml_fd.close()
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.remove_products, str(e)), \
                    None, sys.exc_info()[2]
            finally:
                log (output)
        # END - if file_names

        # Cleanup
        del bands
        del espa_xml
    # END - if products_to_remove
# END - remove_products


#=============================================================================
def build_landsat_science_products (parms):
    '''
    Description:
      Build all the requested science products for Landsat data.
    '''

    # Keep a local options for those apps that only need a few things
    options = parms['options']
    scene = parms['scene']

    # Figure out the metadata filename
    try:
        landsat_metadata = \
            metadata.get_landsat_metadata (options['work_directory'])
    except Exception, e:
        raise ee.ESPAException (ee.ErrorCodes.metadata, str(e)), \
            None, sys.exc_info()[2]
    metadata_filename = landsat_metadata['metadata_filename']

    xml_filename = metadata_filename.replace('_MTL.txt', '.xml')

    # Figure out filenames
    dem_filename = '%s_dem.img' % scene
    solr_filename = '%s-index.xml' % scene

    # Change to the working directory
    current_directory = os.getcwd()
    os.chdir(options['work_directory'])

    output = ''
    try:
        # --------------------------------------------------------------------
        # Convert lpgs to espa first
        # Call with deletion of source files
        cmd = ['convert_lpgs_to_espa', '--del_src_files',
               '--mtl', metadata_filename,
               '--xml', xml_filename]
        cmd = ' '.join(cmd)
        log ('CONVERT LPGS TO ESPA COMMAND:' + cmd)

        try:
            output = util.execute_cmd (cmd)
        except Exception, e:
            raise ee.ESPAException (ee.ErrorCodes.ledaps, str(e)), \
                None, sys.exc_info()[2]
        finally:
            log (output)

        # --------------------------------------------------------------------
        # Generate LEDAPS products SR, TOA, TH
        if options['include_sr'] \
          or options['include_sr_browse'] \
          or options['include_sr_toa'] \
          or options['include_sr_thermal'] \
          or options['include_sr_nbr'] \
          or options['include_sr_nbr2'] \
          or options['include_sr_ndvi'] \
          or options['include_sr_ndmi'] \
          or options['include_sr_savi'] \
          or options['include_sr_msavi'] \
          or options['include_sr_evi'] \
          or options['include_snow_covered_area'] \
          or options['include_surface_water_extent']:
            cmd = ['do_ledaps.py', '--xml', xml_filename]
            cmd = ' '.join(cmd)
            log ('LEDAPS COMMAND:' + cmd)

            try:
                output = util.execute_cmd (cmd)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.ledaps, str(e)), \
                    None, sys.exc_info()[2]
            finally:
                log (output)

        # --------------------------------------------------------------------
        # Generate SR browse product
        # We do not offer browse products for the time being.  When we start
        # offering them again, we should be able to un-comment the following
        # code.  browse.do_sr_browse needs to be updated for the raw_binary
        # format and it should also cleanup any of it's temporary files.
#        if options['include_sr_browse']:
#            try:
#                browse.do_sr_browse (sr_filename, scene,
#                    options['browse_resolution'])
#            except Exception, e:
#                raise ee.ESPAException (ee.ErrorCodes.browse, str(e)), \
#                    None, sys.exc_info()[2]

        # --------------------------------------------------------------------
        # Generate any specified indices
        if options['include_sr_nbr'] \
          or options['include_sr_nbr2'] \
          or options['include_sr_ndvi'] \
          or options['include_sr_ndmi'] \
          or options['include_sr_savi'] \
          or options['include_sr_msavi'] \
          or options['include_sr_evi']:
            cmd = ['do_spectral_indices.py', '--xml', xml_filename]

            # Add the specified index options
            if options['include_sr_nbr']:
                cmd += ['--nbr']
            if options['include_sr_nbr2']:
                cmd += ['--nbr2']
            if options['include_sr_ndvi']:
                cmd += ['--ndvi']
            if options['include_sr_ndmi']:
                cmd += ['--ndmi']
            if options['include_sr_savi']:
                cmd += ['--savi']
            if options['include_sr_msavi']:
                cmd += ['--msavi']
            if options['include_sr_evi']:
                cmd += ['--evi']

            cmd = ' '.join(cmd)
            log ('SPECTRAL INDICES COMMAND:' + cmd)
            try:
                output = util.execute_cmd (cmd)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.spectral_indices,
                    str(e)), None, sys.exc_info()[2]
            finally:
                log (output)
        # END - if indices

        # --------------------------------------------------------------------
        # Create a DEM
        if options['include_snow_covered_area'] \
          or options['include_surface_water_extent']:
            # Does not use our internal raw binary XML format, because it is
            # executing code which comes from Landsat to generate the DEM and
            # because we do not distribute DEM's.
            # Also currently only this Landsat product generation uses the DEM
            # so when another sensor is added that needs to generate a DEM we
            # can consider our choices at that time.
            cmd = ['do_create_dem.py', '--metafile', metadata_filename,
                   '--demfile', dem_filename]
            cmd = ' '.join(cmd)

            log ('CREATE DEM COMMAND:' + cmd)
            try:
                output = util.execute_cmd (cmd)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.create_dem, str(e)), \
                    None, sys.exc_info()[2]
            finally:
                log (output)

        # --------------------------------------------------------------------
        # Generate SOLR index
        if options['include_solr_index']:
            try:
                solr.do_solr_index (landsat_metadata, scene, solr_filename,
                    options['collection_name'])
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.solr, str(e)), \
                    None, sys.exc_info()[2]

        # --------------------------------------------------------------------
        # Generate CFMask product
        if options['include_cfmask'] or options['include_sr']:
            # Load the current ESPA XML file and verify that the TOA bands are
            # present
            espa_xml = metadata_api.parse(xml_filename, silence=True)
            bands = espa_xml.get_bands()
            toa_refl_count = 0
            toa_bt_count = 0
            for band in bands.band:
                if band.product == 'toa_refl':
                    toa_refl_count += 1
                if band.product == 'toa_bt':
                    toa_bt_count += 1
            if (toa_refl_count != 7) or (toa_bt_count !=2):
                raise ee.ESPAException (ee.ErrorCodes.cfmask,
                    "Could not find or missing LEDAPS TOA reflectance"
                    " files in %s" % options['work_directory'])
            del bands    # Not needed anymore
            del espa_xml # Not needed anymore

            cmd = ['cfmask', '--verbose', '--max_cloud_pixels', str(5000000),
                   '--xml', xml_filename]
            cmd = ' '.join(cmd)

            log ('CREATE CFMASK COMMAND:' + cmd)
            try:
                output = util.execute_cmd (cmd)
            except Exception, e:
                raise ee.ESPAException (ee.ErrorCodes.cfmask, str(e)), \
                    None, sys.exc_info()[2]
            finally:
                log (output)

#        # --------------------------------------------------------------------
#        # Generate Surface Water Extent product
#        if options['include_surface_water_extent']:
#            # TODO - Needs modification for XML
#            cmd = ['do_surface_water_extent.py', '--metafile',
#                   metadata_filename, '--reflectance', sr_filename, '--dem',
#                   dem_filename]
#            cmd = ' '.join(cmd)
#
#            log ('CREATE SWE COMMAND:' + cmd)
#            try:
#                output = util.execute_cmd (cmd)
#            except Exception, e:
#                raise ee.ESPAException (ee.ErrorCodes.swe, str(e)), \
#                    None, sys.exc_info()[2]
#            finally:
#                log (output)

#        # --------------------------------------------------------------------
#        # Generate Snow Covered Area product
#        if options['include_snow_covered_area']:
#            # TODO - Needs modification for XML
#            cmd = ['do_snow_cover.py', '--metafile', metadata_filename,
#                   '--toa_infile', toa_filename, '--btemp_infile', th_filename,
#                   '--sca_outfile', sca_filename, '--dem', dem_filename]
#            cmd = ' '.join(cmd)
#
#            log ('CREATE SCA COMMAND:' + cmd)
#            try:
#                output = util.execute_cmd (cmd)
#            except Exception, e:
#                raise ee.ESPAException (ee.ErrorCodes.sca, str(e)), \
#                    None, sys.exc_info()[2]
#            finally:
#                log (output)

        # --------------------------------------------------------------------
        # Remove the intermediate non-product files
        non_products = []
        for item in non_product_files:
            non_products += glob.glob (item)

        # Add L1T source files if not requested
        if not options['include_sourcefile']:
            for item in l1t_source_files:
                non_products += glob.glob (item)
        if not options['include_source_metadata']:
            for item in l1t_source_metadata_files:
                non_products += glob.glob (item)

        cmd = ['rm', '-rf'] + non_products
        cmd = ' '.join(cmd)
        log ('REMOVING INTERMEDIATE DATA COMMAND:' + cmd)

        try:
            output = util.execute_cmd (cmd)
        except Exception, e:
            raise ee.ESPAException (ee.ErrorCodes.cleanup_work_dir, str(e)), \
                None, sys.exc_info()[2]
        finally:
            log (output)

        # Remove generated products that were not requested
        products_to_remove = []
        if not options['include_sourcefile']:
            products_to_remove += \
                [order_to_product_mapping['include_sourcefile']]
        if not options['include_sr']:
            products_to_remove += \
                [order_to_product_mapping['include_sr']]
        if not options['include_sr_toa']:
            products_to_remove += \
                [order_to_product_mapping['include_sr_toa']]
        if not options['include_sr_thermal']:
            products_to_remove += \
                [order_to_product_mapping['include_sr_thermal']]
        # These both need to be false before we delete the fmask files
        # Because our defined SR product includes the fmask band
        if not options['include_cfmask'] and not options['include_sr']:
            products_to_remove += \
                [order_to_product_mapping['include_cfmask']]

        try:
            remove_products (xml_filename, products_to_remove)
        except Exception, e:
            raise ee.ESPAException (ee.ErrorCodes.remove_products, str(e)), \
                None, sys.exc_info()[2]
        finally:
            log (output)

    finally:
        # Change back to the previous directory
        os.chdir(current_directory)

    return xml_filename
# END - build_landsat_science_products


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
    scene = args_dict.pop ('scene')
    options = {k : args_dict[k] for k in args_dict if args_dict[k] != None}

    # Build the JSON parameters dictionary
    json_parms['scene'] = scene
    if sensor not in parameters.valid_sensors:
        log ("Error: Data sensor %s is not implemented" % sensor)
        sys.exit (EXIT_FAILURE)

    json_parms['options'] = options

    sensor = util.getSensor(parms['scene'])

    try:
        # Call the main processing routine
        if sensor in parameters.valid_landsat_sensors:
            validate_landsat_parameters (parms)
            build_landsat_science_products (parms)
        #elif sensor in parameters.valid_OTHER_sensors:
        #    build_OTHER_science_products (parms)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

