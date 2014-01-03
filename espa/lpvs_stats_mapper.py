#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  See 'Description' under '__main__' for more details.
  This mapper performs the statistics portion of LPVS processing.

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import sys
import socket
import json
import traceback
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, debug, set_debug

# local objects and methods
from espa_exception import ErrorCodes, ESPAException
import parameters
from cdr_ecv_landsat import process as process_landsat
import util

#=============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read all lines from STDIN and process them.  Each line is converted to a
      JSON dictionary of the parameters for processing.  Validation is
      performed on the JSON dictionary to test if valid for this mapper.
      After validation the generation of statistics for LPVS is performed.
    '''

    processing_location = socket.gethostname()

    for line in sys.stdin:
        # Reset these for each line
        (server, orderid, sceneid) = (None, None, None)

        try:
            line = str(line).replace('#', '')
            parms = json.loads(line)

            if not parameters.test_for_parameter(parms, 'options'):
                log ("Error missing JSON 'options' record")
                sys.exit(EXIT_FAILURE)

            # Convert the 'options' to a dictionary
            parms['options'] = json.loads(parms['options'])

            (orderid, sceneid) = (parms['orderid'], parms['scene'])

            if parameters.test_for_parameter(parms['options'], 'debug'):
                set_debug(parms['options']['debug'])

            log ("Processing %s:%s" % (orderid, sceneid))

            sensor = util.getSensor(parms['scene'])

            # Update the status in the database
            if parameters.test_for_parameter(parms, 'xmlrpcurl'):
                if parms['xmlrpcurl'] != 'dev':
                    server = xmlrpclib.ServerProxy(parms['xmlrpcurl'])
                    server.updateStatus(sceneid, orderid, processing_location,
                        'processing')

            # Make sure we can process the sensor
            if sensor not in parameters.valid_sensors:
                raise ValueError("Invalid Sensor %s" % sensor)

            #------------------------------------------------------------------
            # NOTE:
            #   The first thing process does is validate the input parameters
            #------------------------------------------------------------------

            # Process the landsat sensors
            if sensor in parameters.valid_landsat_sensors:
                process_landsat (parms)
            #------------------------------------------------------------------
            # NOTE:
            #   Add processing for another sensor here in an 'elif' section
            #------------------------------------------------------------------

        except ESPAException, e:
            # Log the error information
            # Depending on the error_code do something different
            # TODO - Today we are failing everything, but some things can be
            #        recovereable.
            if e.error_code == ErrorCodes.creating_stage_dir \
              or e.error_code == ErrorCodes.creating_work_dir \
              or e.error_code == ErrorCodes.creating_output_dir:

                if server is not None:
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

            elif e.error_code == ErrorCodes.staging_data \
              or e.error_code == ErrorCodes.unpacking:

                if server is not None:
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

            elif e.error_code == ErrorCodes.metadata \
              or e.error_code == ErrorCodes.ledaps \
              or e.error_code == ErrorCodes.browse \
              or e.error_code == ErrorCodes.spectral_indices \
              or e.error_code == ErrorCodes.create_dem \
              or e.error_code == ErrorCodes.solr \
              or e.error_code == ErrorCodes.cfmask \
              or e.error_code == ErrorCodes.cfmask_append \
              or e.error_code == ErrorCodes.swe \
              or e.error_code == ErrorCodes.sca \
              or e.error_code == ErrorCodes.cleanup_work_dir:

                if server is not None:
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

            elif e.error_code == ErrorCodes.warping:

                if server is not None:
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

            elif e.error_code == ErrorCodes.statistics:

                if server is not None:
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

            elif e.error_code == ErrorCodes.packaging_product \
              or e.error_code == ErrorCodes.distributing_product \
              or e.error_code == ErrorCodes.verifying_checksum:

                if server is not None:
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

            else:
                if server is not None:
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

            # Log the error information
            log ("An error occurred processing %s" % sceneid)
            log ("Error: %s" % str(e))
            if hasattr(e, 'output'):
                log ("Error: Code [%s]" % str(e.error_code))
            if hasattr(e, 'output'):
                log ("Error: Output [%s]" % e.output)
            tb = traceback.format_exc()
            log ("Error: Traceback [%s]" % tb)

        except Exception, e:
            if server is not None:
                server.setSceneError(sceneid, orderid, processing_location, e)

            # Log the error information
            log ("An error occurred processing %s" % sceneid)
            log ("Error: %s" % str(e))
            if hasattr(e, 'output'):
                log ("Error: Output [%s]" % e.output)
            tb = traceback.format_exc()
            log ("Error: Traceback [%s]" % tb)
    # END - for line in STDIN

    sys.exit(EXIT_SUCCESS)

