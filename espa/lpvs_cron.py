#! /usr/bin/env python

'''
    FILE: lpvs_cron.py

    PURPOSE: Queries the xmlrpc service to find orders that need to be
             processed and builds/executes a plot.py job to process them.

    PROJECT: Land Satellites Data Systems Science Research and Development
             (LSRD) at the USGS EROS

    LICENSE: NASA Open Source Agreement 1.3

    HISTORY:

    Date              Programmer               Reason
    ----------------  ------------------------ -------------------------------
    Feb/2014          Ron Dilley               Initial implementation
'''

import os
import sys
import time
import json
import xmlrpclib
import subprocess
from datetime import datetime

# espa-common objects and methods
from espa_constants import *
from espa_logging import log

# local objects and methods
import util

#=============================================================================
def usage():
    '''
    Description:
      Display the usage string to the user
    '''

    print ("Usage:")
    print ("\tlpvs_cron.py run-orders | clean-cache")
# END - usage

#=============================================================================
def run_orders():
    '''
    Description:
      Queries the xmlrpc service to see if there are any scenes that need to
      be processed.  If there are, this method builds and executes a plot job
      and updates the status in the database through the xmlrpc service.
    '''

    rpc_url = os.environ.get('ESPA_XMLRPC')
    server = xmlrpclib.ServerProxy(rpc_url)

    # Use the DEV_CACHE_HOSTNAME if present
    dev_cache_hostname = 'DEV_CACHE_HOSTNAME'
    if not os.environ.has_key(dev_cache_hostname) \
      or os.environ.get(dev_cache_hostname) is None \
      or len(os.environ.get(dev_cache_hostname)) < 1:
        espa_cache_host = util.getCacheHostname()
    else:
        espa_cache_host = os.environ.get('DEV_CACHE_HOSTNAME')

    # Use the DEV_CACHE_DIRECTORY if present
    dev_cache_directory = 'DEV_CACHE_DIRECTORY'
    if not os.environ.has_key(dev_cache_directory) \
      or os.environ.get(dev_cache_directory) is None \
      or len(os.environ.get(dev_cache_directory)) < 1:
        espa_cache_directory = '/data2/LSRD'
    else:
        espa_cache_directory = os.environ.get('DEV_CACHE_DIRECTORY')

    try:
        log ("Checking for orders to process...")
        orders = server.getLPVSOrdersToProcess()

        if orders:
            log ("Found orders to process:")

            # Process the orders
            for order in orders:
                log ("Processing order [%s]" % order)

                # Build the order directory
                order_directory = espa_cache_directory + '/' + order

                # Build the plot command line
                cmd = ['./plot.py', '--source_host', espa_cache_host,
                       '--order_directory', order_directory]
                cmd = ' '.join(cmd)
                output = ''
                try:
                    output = util.execute_cmd (cmd)
                except Exception, e:
                    # TODO TODO TODO
                    server.updateOrderStatus (order, 'LPVS cron driver', 'FAIL')
                    # TODO TODO TODO - Exception needs to be better
                    raise e
                finally:
                    log (output)

                # TODO TODO TODO
                server.updateOrderStatus (order, 'LPVS cron driver', 'SUCC')

    finally:
        server = None

# END - run_orders

#=============================================================================
if __name__ == '__main__':
    '''
    Description:
      Read the command line and execute accordingly.
    '''

    if len(sys.argv) != 2:
        usage()
        sys.exit(EXIT_FAILURE)

    # Check required variables that this script should fail on if they are not
    # defined
    required_vars = ('ESPA_XMLRPC', "ESPA_WORK_DIR", "ANC_PATH", "PATH", "HOME")
    for env_var in required_vars:
        if not os.environ.has_key(env_var) or os.environ.get(env_var) is None \
          or len(os.environ.get(env_var)) < 1:
            log ("$%s is not defined... exiting" % env_var)
            sys.exit(-1)

    op = sys.argv[1]
    if op == 'run-orders':
        run_orders()

    elif op == 'clean-cache':
        # TODO TODO TODO
        #cleanDistroCache()
        pass

    else:
        usage()

    sys.exit(EXIT_SUCCESS)

