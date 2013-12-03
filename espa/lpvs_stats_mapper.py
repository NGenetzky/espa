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
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, debug, set_debug

# local objects and methods
from common.parameters import test_for_parameter
from lpvs_generate_stats import process as process_lpvs, \
    validate_input_parameters

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
            json_parms = json.loads(line)

            if not test_for_parameter(json_parms, 'options'):
                log ("Error missing JSON 'options' record")
                sys.exit(EXIT_FAILURE)

            # Convert the 'options' to a dictionary
            json_parms['options'] = json.loads(json_parms['options'])

            # Validate the JSON parameters
            validate_input_parameters(json_parms)

            (orderid, sceneid) = (json_parms['orderid'], json_parms['scene'])

            if json_parms['options']['debug']:
                set_debug()

            log ("Processing %s:%s" % (orderid, sceneid))

            # Update the status in the database
            if test_for_parameter(json_parms, 'xmlrpcurl'):
                server = xmlrpclib.ServerProxy(json_parms['xmlrpcurl'])
                server.updateStatus(sceneid, orderid, processing_location,
                    'processing')

            if process_lpvs(json_parms) != SUCCESS:
                log ("An error occurred processing %s" % sceneid)
                if server is not None: 
                    server.setSceneError(sceneid, orderid,
                        processing_location, e)

        except Exception, e:
            log ("An error occurred processing %s" % sceneid)
            log (str(e))
            if server is not None: 
                server.setSceneError(sceneid, orderid, processing_location, e)
    # END - for line in STDIN

    sys.exit(EXIT_SUCCESS)

