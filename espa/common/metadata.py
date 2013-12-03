
'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Provides routines for retrieving metadata.

History:
  Created Nov/2013 by Ron Dilley, USGS/EROS
'''

import os
import shutil
from cStringIO import StringIO

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, debug


# This contains the valid sensors which are supported
valid_landsat_sensors = ['LT', 'LE']
valid_modis_sensors = ['MODIS']
valid_metadata_sensors = valid_landsat_sensors + valid_modis_sensors


#=============================================================================
def get_landsat_metadata (work_dir):
    '''
    Description:
      Returns the Landsat metadata as a python dictionary
    '''

    # Find the metadata file
    metadata_filename = ''
    dir_items = os.listdir(work_dir)
# TODO TODO TODO - Do we still need to exclude old and lnd?
# TODO TODO TODO - I think the file will be available in the raw binary xml???
    for dir_item in dir_items:
        if (dir_item.find('_MTL') > 0) and \
          not (dir_item.find('old') > 0) and \
          not dir_item.startswith('lnd'):
            # Save the filename and break out of the directory loop
            metadata_filename = dir_item
            log ("Located MTL file:%s" %metadata_filename)
            break

    if metadata_filename =='':
        log ("Could not locate the Landsat MTL file in %s" % work_dir)
        return None

    # Save the current directory and change to the work directory
    current_directory = os.curdir
    os.chdir(work_dir)

# TODO TODO TODO - Do we still need to do these cleanup attempts?
    # Backup the original file
    copy_filename = metadata_filename + '.old'
    shutil.copy(metadata_filename, copy_filename)

    # Read in the file and write it back out to get rid of binary characters
    # at the end of some of the GLS metadata files
    file = open(metadata_filename, 'r')
    file_data = file.readlines()
    file.close()

    buffer = StringIO()
    for line in file_data:
        buffer.write(line)

    # Fix the stupid error where the filename has a bad extention
    metadata_filename = metadata_filename.replace('.TIF', '.txt')

    file = open(metadata_filename, 'w+')
    fixed_data = buffer.getvalue()
    file.write(fixed_data)
    file.flush()
    file.close()
# TODO TODO TODO - Do we still need to do these cleanup attempts?

    # change back to the original directory
    os.chdir(current_directory)

    metadata = dict()
    # First add the filename to the dictionary
    metadata['metadata_filename'] = metadata_filename

    # Read and add the metadata contents to the dictionary
    for line in fixed_data.split('\n'):
        line = line.strip()
        debug (line)
        if not line.startswith('END') and not line.startswith('GROUP'):
            parts = line.split('=')
            if len(parts) == 2:
                metadata[parts[0].strip()] = parts[1].strip().replace('"', '')

    return metadata
# END - get_landsat_metadata


#=============================================================================
def get_metadata (data_sensor, work_dir):
    '''
    Description:
      Returns metadata as a dictionary
    '''

    if data_sensor not in valid_metadata_sensors:
        raise NotImplementedError ("Unsupported data sensor %s" % data_sensor)

    metadata = None

    if data_sensor in valid_landsat_sensors:
        metadata = get_landsat_metadata(work_dir)

    elif data_sensor in valid_modis_sensors:
        raise NotImplementedError ("Data sensor %s is not implemented" % \
            data_sensor)

    return metadata
# END - get_metadata

