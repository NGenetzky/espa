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

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug

# local objects and methods
import common.parameters as parameters
from common.metadata import get_metadata
from products.solr import create_solr_index


# This contains the valid sensors which are supported
valid_landsat_sensors = ['LT', 'LE']
valid_modis_sensors = ['MODIS']
valid_science_sensors = valid_landsat_sensors + valid_modis_sensors

# Default values
default_browse_resolution = 50
default_collection_name = 'DEFAULT_COLLECTION'


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
    # TODO TODO TODO - Need more, but need to implement transfer_data.py first

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
            'include_surface_water_extent', 'create_dem', 'include_solr_index']

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
            options['collection_name'] = default_collection_name

    # TODO TODO TODO TODO TODO TODO TODO TODO - Add more

# END - validate_landsat_parameters


#=============================================================================
def make_browse (scene, browse_resolution=default_browse_resolution):
    '''
    Descrription: TODO TODO TODO
    '''

    log ("Browse Generation Not Implemented!!!!")
    return SUCCESS
# END - make_browse


#=============================================================================
def build_landsat_science_products (parms):
    '''
    Descrription: TODO TODO TODO
    '''

    # Keep a local options for those apps that only need a few things
    options = parms['options']
    scene = parms['scene']

    # Figure out the metadata filename
    metadata = get_metadata (options['sensor'], parms['work_directory'])
    metadata_filename = metadata['metadata_filename']

    # Figure out the DEM filename
    dem_prefix = 'dem.envi' # used to create the DEM filename and for cleanup
    dem_filename = dem_prefix + '.%s.bin' % scene

    # Figure out remaining filenames
    sr_filename = 'lndsr.%s.hdf' % scene
    toa_filename = 'lndcal.%s.hdf' % scene
    th_filename = 'lndth.%s.hdf' % scene
    solr_filename = '%s-index.xml' % scene
    fmask_filename = 'fmask.%s.hdf' % scene
    sca_filename = 'sca.%s.hdf' % scene

    # Change to the working directory
    current_directory = os.curdir
    os.chdir(parms['work_directory'])

    try:
        # Build command line arguments to remove intermediate data files that
        # are not part of the final products
        non_products = glob.glob ('*sixs*')
        non_products += glob.glob ('*metadata*')
        non_products += glob.glob ('LogReport*')
        non_products += glob.glob ('README*')
        non_products += glob.glob ('fmask*txt')

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
          or options['include_sr_evi'] \
          or options['include_snow_covered_area'] \
          or options['include_surface_water_extent']:
            cmd = ['do_ledaps.py', '--metafile', metadata_filename]
            log ("LEDAPS COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # --------------------------------------------------------------------
        # Generate SR browse product
        if options['include_sr_browse']:
            make_browse (scene, options['browse_resolution'])

        # --------------------------------------------------------------------
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

        # --------------------------------------------------------------------
        # Create a DEM
        if options['create_dem'] \
          or options['include_snow_covered_area'] \
          or options['include_surface_water_extent']:
            cmd = ['do_create_dem.py', '--metafile', metadata_filename,
                   '--demfile', dem_filename]

            log ("CREATE DEM COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # --------------------------------------------------------------------
        # Generate SOLR index
        if options['include_solr_index']:
            create_solr_index (metadata, scene, solr_filename,
                options['collection_name'])

        # --------------------------------------------------------------------
        # Generate CFMask product
        if options['include_cfmask'] or options['include_sr']:
            # Verify lndcal file exists first
            if not os.path.isfile(toa_filename):
                raise RuntimeError (("Could not find LEDAPS TOA reflectance"
                    " file in %s") % parms['work_directory'])

            # TODO TODO TODO - I wonder if this should be a 'do_cfmask.py'
            cmd = ['cfmask', '--verbose', '--toarefl=%s' % toa_filename]

            log ("CREATE CFMASK COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # --------------------------------------------------------------------
        # Append CFMask into the SR product if only SR was selected
        if options['include_sr'] and not options['include_cfmask']:
            cmd = ['do_append_cfmask.py', '--sr_infile', sr_filename,
                   '--cfmask_infile', fmask_filename]

            log ("APPEND CFMASK COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # --------------------------------------------------------------------
        # Generate Surface Water Extent product
        if options['include_surface_water_extent']:
            cmd = ['do_surface_water_extent.py', '--metafile',
                   metadata_filename, '--reflectance', sr_filename, '--dem',
                   dem_filename]

            log ("CREATE SWE COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # --------------------------------------------------------------------
        # Generate Snow Covered Area product
        if options['include_snow_covered_area']:
            cmd = ['do_snow_cover.py', '--metafile', metadata_filename,
                   '--toa_infile', toa_filename, '--btemp_infile', th_filename,
                   '--sca_outfile', sca_filename, '--dem', dem_filename]

            log ("CREATE SCA COMMAND:%s" % ' '.join(cmd))
            output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
            log (output)

        # --------------------------------------------------------------------
        # Remove non product files here
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
        if not options['create_dem']:
            non_products += glob.glob ('dem*')
        if not options['include_cfmask']:
            non_products += glob.glob ('fmask*')
        cmd = ['rm', '-rf'] + non_products
        log ("REMOVING INTERMEDIATE DATA COMMAND:%s" % ' '.join(cmd))
        output = subprocess.check_output (cmd, stderr=subprocess.STDOUT)
        log (output)
    except Exception, e:
        raise e
    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
# END - build_landsat_science_products


#=============================================================================
def build_science_products (parms):
    '''
    Descrription: TODO TODO TODO
    '''

    options = parms['options']
    sensor = options['sensor']

    if sensor not in valid_science_sensors:
        raise NotImplementedError ("Unsupported data sensor %s" % sensor)

    if sensor in valid_landsat_sensors:
        # Validate the parameters
        validate_landsat_parameters (parms)
        debug (parms)

        build_landsat_science_products (parms)

    elif sensor in valid_modis_sensors:
        raise NotImplementedError ("Data sensor %s is not implemented" % \
            data_source)
# END - build_science_products


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
        build_science_products (parms)
    except Exception, e:
        log (str(e))
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

