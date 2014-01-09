#! /usr/bin/env python

'''
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


#==============================================================================
def usage():
    '''
    Description:
      Display the usage string to the user
    '''

    print ("Usage:")
    print ("\tlpvs_cron.py run-scenes | clean-cache")


#==============================================================================
if __name__ == '__main__':
    '''
    Description:
      TODO TODO TODO
    '''

    if len(sys.argv) != 2:
        usage()
        sys.exit(EXIT_FAILURE)

