#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  See 'Description' under '__main__' for more details.
  TODO TODO TODO

History:
  Original Development (cdr_ecv.py) by David V. Hill, USGS/EROS
  Created Nov/2013 by Ron Dilley, USGS/EROS
    - Gutted the original implementation from cdr_ecv.py and placed it in this
      file.
'''

import os
import sys
import subprocess
import glob
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
import common.parameters as parameters
from common.metadata import get_metadata
from products.solr import create_solr_index
import common.util as util


# Default values
default_browse_resolution = 50
default_solr_collection_name = 'DEFAULT_COLLECTION'


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

    parameters.add_scene_parameter (parser)

    parameters.add_work_directory_parameter (parser)

    parameters.add_data_type_parameter (parser, parameters.valid_data_types)

    parameters.add_science_product_parameters (parser)

    return parser
# END - build_argument_parser


#==============================================================================
def validate_build_landsat_parameters (parms):
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
            'include_sr_evi', 'include_snow_covered_area',
            'include_surface_water_extent', 'include_solr_index',
            'include_dem']

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
# END - validate_build_landsat_parameters


#==============================================================================
def make_browse (scene, browse_resolution=default_browse_resolution):
    '''
    Description: TODO TODO TODO
    '''
    # TODO TODO TODO - Implement Me!!!!!!!!!!!!!!!!!!!!

    log ("Browse Generation Not Implemented!!!!")
    return SUCCESS
# END - make_browse


#==============================================================================
def build_landsat_science_products (parms):
    '''
    Description:
      Build all the requested science products for Landsat data.
    '''

    # Keep a local options for those apps that only need a few things
    options = parms['options']
    scene = parms['scene']

    # Figure out the metadata filename
    metadata = get_metadata (options['sensor'], options['work_directory'])
    metadata_filename = metadata['metadata_filename']

    # Figure out filenames
    sr_filename = 'lndsr.%s.hdf' % scene
    toa_filename = 'lndcal.%s.hdf' % scene
    th_filename = 'lndth.%s.hdf' % scene
    fmask_filename = 'fmask.%s.hdf' % scene
    dem_filename = 'dem.%s.bin' % scene
    sca_filename = 'sca.%s.hdf' % scene
    solr_filename = '%s-index.xml' % scene

    # Change to the working directory
    current_directory = os.curdir
    os.chdir(options['work_directory'])

    try:
        # ---------------------------------------------------------------------
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
          or options['include_sr_evi'] \
          or options['include_snow_covered_area'] \
          or options['include_surface_water_extent']:
            cmd = ['do_ledaps.py', '--metafile', metadata_filename]
            log ("LEDAPS COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # ---------------------------------------------------------------------
        # Generate SR browse product
        if options['include_sr_browse']:
            make_browse (scene, options['browse_resolution'])

        # ---------------------------------------------------------------------
        # Generate any specified indices
        if options['include_sr_nbr'] \
          or options['include_sr_nbr2'] \
          or options['include_sr_ndvi'] \
          or options['include_sr_ndmi'] \
          or options['include_sr_savi'] \
          or options['include_sr_evi']:
            cmd = ['do_spectral_indices.py']

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
            if options['include_sr_evi']:
                cmd += ['--evi']

            # We are always generating indices off of surface reflectance
            cmd += ['-i', sr_filename]

            log ("SPECTRAL INDICES COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)
        # END - if indices

        # ---------------------------------------------------------------------
        # Create a DEM
        if options['include_dem'] \
          or options['include_snow_covered_area'] \
          or options['include_surface_water_extent']:
            cmd = ['do_create_dem.py', '--metafile', metadata_filename,
                   '--demfile', dem_filename]

            log ("CREATE DEM COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # ---------------------------------------------------------------------
        # Generate SOLR index
        if options['include_solr_index']:
            create_solr_index (metadata, scene, solr_filename,
                options['collection_name'])

        # ---------------------------------------------------------------------
        # Generate CFMask product
        if options['include_cfmask'] or options['include_sr']:
            # Verify lndcal file exists first
            if not os.path.isfile(toa_filename):
                raise RuntimeError (("Could not find LEDAPS TOA reflectance"
                    " file in %s") % options['work_directory'])

            # TODO TODO TODO - I wonder if this should be a 'do_cfmask.py'
            cmd = ['cfmask', '--verbose', '--toarefl=%s' % toa_filename]

            log ("CREATE CFMASK COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # ---------------------------------------------------------------------
        # Append CFMask into the SR product if only SR was selected
        if options['include_sr'] and not options['include_cfmask']:
            cmd = ['do_append_cfmask.py', '--sr_infile', sr_filename,
                   '--cfmask_infile', fmask_filename]

            log ("APPEND CFMASK COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # ---------------------------------------------------------------------
        # Generate Surface Water Extent product
        if options['include_surface_water_extent']:
            cmd = ['do_surface_water_extent.py', '--metafile',
                   metadata_filename, '--reflectance', sr_filename, '--dem',
                   dem_filename]

            log ("CREATE SWE COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # ---------------------------------------------------------------------
        # Generate Snow Covered Area product
        if options['include_snow_covered_area']:
            cmd = ['do_snow_cover.py', '--metafile', metadata_filename,
                   '--toa_infile', toa_filename, '--btemp_infile', th_filename,
                   '--sca_outfile', sca_filename, '--dem', dem_filename]

            log ("CREATE SCA COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # ---------------------------------------------------------------------
        # Remove non-product (intermediate) files here
        non_products = glob.glob ('*sixs*')
        non_products += glob.glob ('*metadata*')
        non_products += glob.glob ('LogReport*')
        non_products += glob.glob ('README*')
        non_products += glob.glob ('fmask*txt')

        if not options['include_sourcefile']:
            non_products += glob.glob ('*TIF')
            non_products += glob.glob ('*gap_mask*')
        if not options['include_source_metadata']:
            non_products += glob.glob ('*MTL*')
            non_products += glob.glob ('*VER*')
            non_products += glob.glob ('*GCP*')
        if not options['include_sr']:
            non_products += glob.glob ('lndsr*')
        if not options['include_sr_toa']:
            non_products += glob.glob ('lndcal*')
        if not options['include_sr_thermal']:
            non_products += glob.glob ('lndth*')
        if not options['include_sr_browse']:
            non_products += glob.glob ('*browse*')
        if not options['include_dem']:
            non_products += glob.glob ('dem*')
        if not options['include_cfmask']:
            non_products += glob.glob ('fmask*')

        cmd = ['rm', '-rf'] + non_products
        log ("REMOVING INTERMEDIATE DATA COMMAND:%s" % ' '.join(cmd))
        subprocess.check_output (cmd, stderr=subprocess.STDOUT)

    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
# END - build_landsat_science_products


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
            validate_build_landsat_parameters (parms)
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

