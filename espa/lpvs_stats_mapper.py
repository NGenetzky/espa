#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description: TODO TODO TODO

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import sys
import socket
import json
import numpy as np
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import *
from espa_logging import log

from lpvs import process as process_lpvs
#from espa_build_science_products import build_science_products
#from espa_generate_tiles import generate_tiles
#from lpvs_generate_tiles import generate_stats

#=============================================================================
if __name__ == '__main__':
    '''
    Description: TODO TODO TODO
    '''

    processing_location = socket.gethostname()
    (server, sceneid) = (None, None)

    for line in sys.stdin:
        try:
            line = str(line).replace('#', '')
#            line = json.loads(line)
#            (orderid, sceneid) = (line['orderid'], line['scene'])
#
#            if type(line['options']) in (str, unicode):
#                options = json.loads(line['options'])
#            else:
#                options = line['options']
#
#            if line.has_key('xmlrpcurl'):    
#                xmlrpcurl = line['xmlrpcurl']
#            else:
#                xmlrpcurl = None
#        
#            if (not sceneid.startswith('L')): 
#                logger(sceneid, "sceneid did not start with L")
#                continue;
#        
#            log ("Processing %s:%s" % (orderid, sceneid))
#
#            if xmlrpcurl is not None:
#                server = xmlrpclib.ServerProxy(xmlrpcurl)
#                server.updateStatus(sceneid, orderid,processing_location,
#                    'processing')
#
#            #=================================================================
#            build_product_cmd = './espa_build_science_products.py'
#            build_product_cmd += ' --order %s' % orderid
#            build_product_cmd += ' --scene %s' % sceneid
#
#            print build_product_cmd
##########################
##########################
##########################
#
#            #=================================================================
#            build_product_cmd = './lpvs_generate_stats.py'
#            build_product_cmd += ' --order %s' % orderid
#            build_product_cmd += ' --scene %s' % sceneid
#
#            print build_product_cmd
##########################
##########################
##########################
##########################

        except Exception, e:
            log ("An error occurred processing %s" % sceneid)
            log (str(e))
            if server is not None: 
                server.setSceneError(sceneid, orderid, processing_location, e)
    # END - for line

