#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description: TODO TODO TODO

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import errno
import sys
import uuid
import shutil
import subprocess
import ftplib
import urllib

# espa-common objects and methods
from espa_constants import *
from espa_logging import log


#=============================================================================
def copy_file_to_file (source_file, destination_file):
    '''
    Description:
      Use unix 'cp' to copy a file from one place to another on the localhost.
    '''

    cmd = ['cp', source_file, destination_file]

    # Transfer the data and raise any errors
    output = ''
    try:
        output = subprocess.check_output (cmd)
    except Exception, e:
        log ("Error: Failed to copy file")
        raise e
    finally:
        log (output)

    log ("Transfer complete - CP")
# END - copy_file_to_directory


#=============================================================================
def remote_copy_file_to_file (source_host, source_file, destination_file):
    '''
    Description:
      Use unix 'cp' to copy a file from one place to another on a remote
      machine using ssh.
    '''

    cmd = ['ssh', source_host, 'cp', source_file, destination_file]

    # Transfer the data and raise any errors
    output = ''
    try:
        output = subprocess.check_output (cmd)
    except Exception, e:
        log ("Error: Failed to copy file")
        raise e
    finally:
        log (output)

    log ("Transfer complete - SSH-CP")
# END - remote_copy_file_to_directory


#=============================================================================
def ftp_from_remote_location(username, pw, host, remotefile, localfile):
    '''
    Author: David Hill

    Date: 12/5/13

    Description:
      Transfers files from a remote location to the local machine using ftplib.

    Parameters:
      username = Username for ftp account
      pw = Password for ftp account
      host = The ftp server host
      remotefile = The file to transfer
      localfile = Full path to where the local file should be created.
                  (Parent directories must exist)

    Returns: None

    Errors: Raises Exception() in the event of error
    '''

    # Make sure the src_file is absolute, otherwise ftp will choke
    if not remotefile.startswith('/'):
        remotefile = '/' + remotefile

    pw = urllib.unquote(pw)

    url = 'ftp://%s/%s' % (host, remotefile)

    log ("Transferring file from %s to %s" % (url, localfile))
    ftp = None
    try:
        with open(localfile, 'wb') as loc_file:
            def callback(data):
                loc_file.write(data)

            ftp = ftplib.FTP(host, timeout=30)
            ftp.login(user=username, passwd=pw)
            ftp.set_debuglevel(0)
            ftp.retrbinary("RETR " + remotefile, callback)

    finally:
        if ftp:
            ftp.quit()

    log ("Transfer complete - FTP")
# END - ftp_from_remote_location


#=============================================================================
def ftp_to_remote_location(username, pw, localfile, host, remotefile):
    '''
    Author: David Hill

    Date: 12/5/13

    Description:
      Transfers files from the local machine to a remote location using ftplib.

    Parameters:
      username = Username for ftp account
      pw = Password for ftp account
      host = The ftp server host
      remotefile = Full path of where to store the file (Directories must exist)
      localfile = Full path of file to transfer out

    Returns: None

    Errors: Raises Exception() in the event of error
    '''

    # Make sure the src_file is absolute, otherwise ftp will choke
    if not remotefile.startswith('/'):
        remotefile = '/' + remotefile

    pw = urllib.unquote(pw)

    log ("Transferring file from %s to %s" % \
        (localfile, 'ftp://%s/%s' % (host, remotefile)))

    ftp = None

    try:
        log ("Logging into %s with %s:%s" % (host, username, pw))
        ftp = ftplib.FTP(host, user=username, passwd=pw, timeout=30)
        ftp.storbinary("STOR " + remotefile, open(localfile, 'rb'), 1024)
    finally:
        if ftp:
            ftp.quit()

    log ("Transfer complete - FTP")
# END - ftp_to_remote_location


#=============================================================================
def scp_transfer_file (source_host, source_file,
                       destination_host, destination_file):
    '''
    Description:
      Using SCP transfer a file from a source location to a destination
      location.
    '''

    cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-c', 'arcfour', '-C']

    # Build the source portion of the command
    if source_host == 'localhost':
        cmd += [source_file]
    elif source_host != destination_host:
        # Build the SCP command line
        cmd += ['%s:%s' % (source_host, source_file)]

    # Build the destination portion of the command
    if destination_host == 'localhost':
        cmd += [destination_file]
    elif source_host != destination_host:
        cmd += ['%s:%s' % (destination_host, destination_file)]

    # Transfer the data and raise any errors
    output = ''
    try:
        output = subprocess.check_output (cmd)
    except Exception, e:
        log ("Error: Failed to transfer data")
        raise e
    finally:
        log (output)

    log ("Transfer complete - SCP")
# END - scp_transfer_file


#=============================================================================
def transfer_file (source_host, source_file,
                   destination_host, destination_file,
                   source_username=None, source_pw=None,
                   destination_username=None, destination_pw=None):
    '''
    Description:
      Using cp/FTP/SCP transfer a file from a source location to a destination
      location.

    Notes:
      We are not doing anything significant here other then some logic and
      fallback to SCP if FTP fails.

    '''

    log ("Transfering [%s:%s] to [%s:%s]" % \
        (source_host, source_file, destination_host, destination_file))

    # If both source and destination are localhost we can just copy the data
    if source_host == 'localhost' and destination_host == 'localhost':
        copy_file_to_file (source_file, destination_file)
        return

    # If both source and destination hosts are the same, we can use ssh to copy
    # the files locally on the remote host
    if source_host == destination_host:
        remote_copy_file_to_file (source_host, source_file, destination_file)
        return

    # Try FTP first before SCP if usernames and passwords are provided
    if source_username is not None and source_pw is not None:
        try:
            ftp_from_remote_location (source_username, source_pw, source_host,
                source_file, destination_file)
            return
        except Exception, e:
            log ("Warning: FTP failures will attempt transfer using SCP")
            log ("FTP Errors: %s" % str(e))

    elif destination_username is not None and destination_pw is not None:
        try:
            ftp_to_remote_location (destination_username, destination_pw,
                source_file, destination_host, destination_file)
            return
        except Exception, e:
            log ("Warning: FTP failures will attempt transfer using SCP")
            log ("FTP Errors: %s" % str(e))

    # As a last resort try SCP
    scp_transfer_file (source_host, source_file,
                       destination_host, destination_file)
# END - transfer_file

