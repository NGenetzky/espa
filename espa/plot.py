#! /usr/bin/env python

'''
License:
  "NASA Open Source Agreement 1.3"

Description:

History:
  Original Development Jan/2014 by Ron Dilley, USGS/EROS
'''

import os
import sys
import glob
import shutil
import datetime
import calendar
import subprocess
import traceback
from cStringIO import StringIO
from argparse import ArgumentParser
from collections import defaultdict
from matplotlib import pyplot as mpl_plot
from matplotlib import dates as mpl_dates

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug


#=============================================================================
def execute_cmd (cmd):
    '''
    Description:
      Execute a command line and return SUCCESS or ERROR

    Returns:
        output - The stdout and/or stderr from the executed command.
    '''

    output = ''
    proc = None
    try:
        proc = subprocess.Popen (cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        output = proc.communicate()[0]

        if proc.returncode < 0:
            message = "Application terminated by signal [%s]" % cmd
            raise Exception (message)

        if proc.returncode != 0:
            message = "Application failed to execute [%s]" % cmd
            raise Exception (message)

        application_exitcode = proc.returncode >> 8
        if application_exitcode != 0:
            message = "Application [%s] returned error code [%d]" \
                % (cmd, application_exitcode)
            raise Exception (message)

    finally:
        del proc

    return output
# END - execute_cmd


#==============================================================================
def scp_transfer_file (source_host, source_file,
                       destination_host, destination_file):
    '''
    Description:
      Using SCP transfer a file from a source location to a destination
      location.

    Note:
      - It is assumed ssh has been setup for access between the localhost
        and destination system
      - If wild cards are to be used with the source, then the destination
        file must be a directory.  ***No checking is performed in this code***
    '''

    cmd = ['scp', '-q', '-o', 'StrictHostKeyChecking=no', '-c', 'arcfour', '-C']

    # Build the source portion of the command
    # Single quote the source to allow for wild cards
    if source_host == 'localhost':
        cmd += [source_file]
    elif source_host != destination_host:
        # Build the SCP command line
        cmd += ["'%s:%s'" % (source_host, source_file)]

    # Build the destination portion of the command
    cmd += ['%s:%s' % (destination_host, destination_file)]

    cmd = ' '.join(cmd)

    # Transfer the data and raise any errors
    output = ''
    try:
        output = execute_cmd (cmd)
    except Exception, e:
        log (output)
        log ("Error: Failed to transfer data")
        raise e

    log ("Transfer complete - SCP")
# END - scp_transfer_file


#=============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser
    '''

    # Create a command line argument parser
    description = "Generate plots of the statistics"
    parser = ArgumentParser (description=description)

    parser.add_argument ('--debug',
        action='store_true', dest='debug', default=False,
        help="turn debug logging on")

    parser.add_argument ('--source_host',
        action='store', dest='source_host', default='localhost',
        help="hostname where the order resides")

    parser.add_argument ('--order_directory',
        action='store', dest='order_directory', required=True,
        help="directory on the source host where the order resides")

    parser.add_argument ('--stats_directory',
        action='store', dest='stats_directory', default=os.curdir,
        help="directory containing the statistics")

    parser.add_argument ('--plot_directory',
        action='store', dest='plot_directory', default=os.curdir,
        help="directory to place the plots")

    parser.add_argument ('--keep',
        action='store_true', dest='keep', default=False,
        help="keep the working directory")

    return parser
# END - build_argument_parser


#=============================================================================
def read_stats(stat_file):
    '''
    Description:
      Read the file contents and return as a list of key values
    '''

    stat_fd = open(stat_file, 'r')

    try:
        for line in stat_fd:
            line_lower = line.strip().lower()
            parts = line_lower.split('=')
            yield(parts)

    finally:
        stat_fd.close()

# END - read_stats


#=============================================================================
def get_mdom_from_ydoy(year, day_of_year):
    '''
    Description:
      Determine month and day_of_month from the year and day_of_year
    '''

    # Convert DOY to month and day
    month = 1
    day_of_month = day_of_year
    while month < 13:
        month_days = calendar.monthrange(year, month)[1]
        if day_of_month <= month_days:
            return (month, day_of_month)
        day_of_month -= month_days
        month += 1
# END - get_mdom_from_ydoy


#=============================================================================
def get_ymdl_from_filename(filename):
    '''
    Description:
      Determine the year, month, and day_of_month from the scene name
    '''

    year = 0
    month = 0
    day_of_month = 0
    symbol = 'rx'
    label = 'unk'

    if filename.startswith('MOD'):
        date_element = filename.split('.')[1]
        year = int(date_element[1:5])
        day_of_year = int(date_element[5:8])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'Terra'

    elif filename.startswith('MYD'):
        date_element = filename.split('.')[1]
        year = int(date_element[1:5])
        day_of_year = int(date_element[5:8])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'Aqua'

    elif 'LT4' in filename:
        date_element = filename.split('.')[1]
        year = int(date_element[9:13])
        day_of_year = int(date_element[13:16])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'LT4'

    elif 'LT5' in filename:
        date_element = filename.split('.')[1]
        year = int(date_element[9:13])
        day_of_year = int(date_element[13:16])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'LT5'

    elif 'LE7' in filename:
        date_element = filename.split('.')[1]
        year = int(date_element[9:13])
        day_of_year = int(date_element[13:16])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'LE7'

    return (year, month, day_of_month, label)
# END - get_ymdl_from_filename


#=============================================================================
def generate_sensor_stats(stat_name, stat_files):
    '''
    Description:
      Combines all the stat files for one sensor into one csv file.
    '''

    stats = dict()

    # Fix the output filename
    out_filename = stat_name.replace(' ', '_').lower()
    out_filename += '_stats.csv'

    # Read each file into a dictionary
    for stat_file in stat_files:
        stats[stat_file] = \
            dict((key, value) for (key, value) in read_stats(stat_file))

    stat_data = list()
    # Process through and create records
    for filename, obj in stats.items():
        debug (filename)
        # Figure out the date for stats record
        (year, month, day_of_month, label) = get_ymdl_from_filename(filename)
        date = '%04d-%02d-%02d' % (int(year), int(month), int(day_of_month))
        debug (date)

        line = '%s,%s,%s,%s,%s' \
            % (date, obj['minimum'], obj['maximum'], obj['mean'], obj['stddev'])
        debug (line)

        stat_data += [line]

    # Create an empty string buffer to hold the output
    buffer = StringIO()

    # Write the file header
    buffer.write('DATE,MINIMUM,MAXIMUM,MEAN,STDDEV')

    # Sort the stats into the buffer
    for line in sorted(stat_data):
        buffer.write('\n')
        buffer.write(line)

    # Flush and save the buffer as a string
    buffer.flush()
    data = buffer.getvalue()
    buffer.close()

    # Create the output file
    fd = open(out_filename, 'w')
    fd.write(data)
    fd.flush()
    fd.close()
# END - generate_sensor_stats


# Specify a base number of days to expand the plot date range
# This helps keep data points from being placed on the plot border lines
TIME_DELTA_5_DAYS = datetime.timedelta(days=5)
#=============================================================================
def generate_plot(plot_name, subject, stats):
    '''
    Description:
      Builds a plot and then generates a png formatted image of the plot. 
    '''

    auto_date_locator = mpl_dates.AutoDateLocator()
    aut_date_formatter = mpl_dates.AutoDateFormatter(auto_date_locator)

    lower_subject = subject.lower()

    # Create the subplot objects
    #(fig, min_plot) = mpl_plot.subplots()
    fig = mpl_plot.figure()
    min_plot = mpl_plot.subplot(111)

    # Adjust the figure size
    fig.set_size_inches(11, 8.5)

    #-------------------------------------------------------------------------
    # Build a dictionary of labels which contains lists of the values, while
    # determining the minimum and maximum values to be displayed
    plot_y_min = 99999 # Our data is 16bit so this should be good enough
    plot_y_max = -99999 # Our data is 16bit so this should be good enough
    # I won't be here to resolve this
    plot_date_min = datetime.date(9998, 12, 31)
    # Doubt if we have any this old
    plot_date_max = datetime.date(1900, 01, 01)

    label_dict = defaultdict(list)
    for filename, obj in stats.items():
        debug (filename)
        # Figure out the date for plotting
        (year, month, day_of_month, label) = get_ymdl_from_filename(filename)
        debug (' '.join([str(year), str(month), str(day_of_month)]))
        date = datetime.date(year, month, day_of_month)

        value = float(obj[lower_subject])
        debug (value)

        label_dict[label].append((date, value))

        if value < plot_y_min:
            plot_y_min = value
        if value > plot_y_max:
            plot_y_max = value

        if date < plot_date_min:
            plot_date_min = date
        if date > plot_date_max:
            plot_date_max = date

    #-------------------------------------------------------------------------
    # Convert the label dictionary values into lists appropriate for the plot
    for label, obj in label_dict.items():
        dates = list()
        values = list()
        symbol = 'rx'

        if label == 'Terra':
            symbol = 'mo'
        elif label == 'Aqua':
            symbol = 'co'
        elif label == 'LT4':
            symbol = 'rD'
        elif label == 'LT5':
            symbol = 'gD'
        elif label == 'LE7':
            symbol = 'bD'

        for date, value in obj:
            debug (' '.join([label, str(date), str(value), symbol]))
            dates.append(date)
            values.append(value)

        # Finally plot the lists of dates and values
        min_plot.plot(dates, values, symbol, markersize=4.0, label=label)

    # Adjust the y range to help move them from the edge of the plot
    y_diff = plot_y_max - plot_y_min
    if y_diff < 2:
        # If our range is really small, then 5 is too big
        delta = 1
    else:
        delta = 5
    for increment in range(0, int(y_diff/200) + 1):
        # Add delta to each end of the range for every 200
        # With a minimum of delta added to each end of the range
        plot_y_min -= delta
        plot_y_max += delta
    debug (plot_y_min)
    debug (plot_y_max)

    # Adjust the day range to help move them from the edge of the plot
    date_diff = plot_date_max - plot_date_min
    debug (date_diff.days)
    for increment in range(0, int(date_diff.days/365) + 1):
        # Add 5 days to each end of the range for each year
        # With a minimum of 5 days added to each end of the range
        plot_date_min -= TIME_DELTA_5_DAYS
        plot_date_max += TIME_DELTA_5_DAYS
    debug (plot_date_min)
    debug (plot_date_max)

    # X Axis details
    min_plot.xaxis.set_major_locator(auto_date_locator)
    min_plot.xaxis.set_major_formatter(aut_date_formatter)
    min_plot.xaxis.set_minor_locator(auto_date_locator)

    # X Axis - Limits - Determine the date range of the to-be-displayed data
    min_plot.set_xlim(plot_date_min, plot_date_max)

    # X Axis - Label - Will always be 'Date'
    mpl_plot.xlabel('Date')

    # Y Axis - Limits
    min_plot.set_ylim(plot_y_min, plot_y_max)

    # Y Axis - Label
    # We are going to make the Y Axis Label the title for now (See Title)
    #mpl_plot.ylabel(subject)

    # Plot - Title
    plot_name += ' - ' + subject
    #mpl_plot.title(plot_name)
    # The Title gets covered up by the legend so use the Y Axis Label
    mpl_plot.ylabel(plot_name)

    mpl_plot.legend(bbox_to_anchor=(0.0, 1.01, 1.0, 0.5), loc=3, ncol=5,
        mode="expand", borderaxespad=0.0, numpoints=1, prop={'size':12})

    # Fix the filename and save the plot
    filename = plot_name.replace('- ', '').lower()
    filename = filename.replace(' ', '_')
    filename += '_plot'

    # Adjust the margins to be a little better
    mpl_plot.subplots_adjust(left=0.1, right=0.92, top=0.9, bottom=0.1)

    # Save the plot to a file
    mpl_plot.savefig('%s.png' % filename, dpi=100)

    # Close the plot so we can open another one
    mpl_plot.close()
# END - generate_plot


#=============================================================================
def generate_plots(plot_name, stat_files):
    '''
    Description:
      Gather all the information needed for plotting from the files and
      generate a plot for each statistic
    '''

    stats = dict()

    # Read each file into a dictionary
    for stat_file in stat_files:
        debug (stat_file)
        stats[stat_file] = \
            dict((key, value) for (key, value) in read_stats(stat_file))

    generate_plot(plot_name, 'Minimum', stats)
    generate_plot(plot_name, 'Maximum', stats)
    generate_plot(plot_name, 'Mean', stats)
    generate_plot(plot_name, 'StdDev', stats)
# END - generate_plots


#=============================================================================
def process_band_type(sensor_info, band_type):
    '''
    Description:
      A generic processing routine which finds the files to process based on
      the provided search criteria.  Utilizes the provided band type as part
      of the plot names and filenames.  If no files are found, no plots or
      combined statistics will be generated.
    '''

    single_sensor_files = list()
    multi_sensor_files = list()
    single_sensor_name = ''
    sensor_count = 0 # How many sensors were found....
    for (search_string, sensor_name) in sensor_info:
        single_sensor_files = glob.glob(search_string)
        if single_sensor_files and single_sensor_files != None:
            if len(single_sensor_files) > 0:
                sensor_count += 1 # We found another sensor
                single_sensor_name = sensor_name
                generate_sensor_stats ("%s %s" % (sensor_name, band_type),
                    single_sensor_files)
                multi_sensor_files += single_sensor_files

    # Cleanup the memory for this while we process the multi-sensor list
    del single_sensor_files

    # We always use the multi sensor variable here because it will only have
    # the single sensor in it, if that is the case
    if sensor_count > 1:
        generate_plots ("Multi Sensor %s" % band_type,
            multi_sensor_files)
    elif sensor_count == 1:
        generate_plots ("%s %s" % (single_sensor_name, band_type),
            multi_sensor_files)
    # Else do not plot

    # Remove the processed files
    if sensor_count > 0:
        for file in multi_sensor_files:
            if os.path.exists(file):
                os.unlink(file)

    del multi_sensor_files
# END - process_band_type


##############################################################################
# Define the configuration for searching for files and some of the text for
# the plots and filenames.  Doing this greatly simplified the code. :)
# Should be real easy to add others. :)

L4_SATELLITE_NAME = 'Landsat 4'
L5_SATELLITE_NAME = 'Landsat 5'
L7_SATELLITE_NAME = 'Landsat 7'
TERRA_SATELLITE_NAME = 'Terra'
AQUA_SATELLITE_NAME = 'Aqua'

# Only Landsat band 6 files
THERMAL_SENSOR_INFO = [('lndsr.LT4*band6.stats', L4_SATELLITE_NAME),
                       ('lndsr.LT5*band6.stats', L5_SATELLITE_NAME),
                       ('lndsr.LE7*band6.stats', L7_SATELLITE_NAME)]

# Only MODIS band 5 files
SWIR_MODIS_B5_SENSOR_INFO = [('MOD*sur_refl*b05.stats', TERRA_SATELLITE_NAME),
                             ('MYD*sur_refl*b05.stats', AQUA_SATELLITE_NAME)]

# MODIS band 6 maps to Landsat band 5
SWIR1_SENSOR_INFO = [('lndsr.LT4*band5.stats', L4_SATELLITE_NAME),
                     ('lndsr.LT5*band5.stats', L5_SATELLITE_NAME),
                     ('lndsr.LE7*band5.stats', L7_SATELLITE_NAME),
                     ('MOD*sur_refl*6.stats', TERRA_SATELLITE_NAME),
                     ('MYD*sur_refl*6.stats', AQUA_SATELLITE_NAME)]

# MODIS band 7 maps to Landsat band 7
SWIR2_SENSOR_INFO = [('lndsr.LT4*band7.stats', L4_SATELLITE_NAME),
                     ('lndsr.LT5*band7.stats', L5_SATELLITE_NAME),
                     ('lndsr.LE7*band7.stats', L7_SATELLITE_NAME),
                     ('MOD*sur_refl*7.stats', TERRA_SATELLITE_NAME),
                     ('MYD*sur_refl*7.stats', AQUA_SATELLITE_NAME)]

# MODIS band 3 maps to Landsat band 1
BLUE_SENSOR_INFO = [('lndsr.LT4*band1.stats', L4_SATELLITE_NAME),
                    ('lndsr.LT5*band1.stats', L5_SATELLITE_NAME),
                    ('lndsr.LE7*band1.stats', L7_SATELLITE_NAME),
                    ('MOD*sur_refl*3.stats', TERRA_SATELLITE_NAME),
                    ('MYD*sur_refl*3.stats', AQUA_SATELLITE_NAME)]

# MODIS band 4 maps to Landsat band 2
GREEN_SENSOR_INFO = [('lndsr.LT4*band2.stats', L4_SATELLITE_NAME),
                     ('lndsr.LT5*band2.stats', L5_SATELLITE_NAME),
                     ('lndsr.LE7*band2.stats', L7_SATELLITE_NAME),
                     ('MOD*sur_refl*4.stats', TERRA_SATELLITE_NAME),
                     ('MYD*sur_refl*4.stats', AQUA_SATELLITE_NAME)]

# MODIS band 1 maps to Landsat band 3
RED_SENSOR_INFO = [('lndsr.LT4*band3.stats', L4_SATELLITE_NAME),
                   ('lndsr.LT5*band3.stats', L5_SATELLITE_NAME),
                   ('lndsr.LE7*band3.stats', L7_SATELLITE_NAME),
                   ('MOD*sur_refl*1.stats', TERRA_SATELLITE_NAME),
                   ('MYD*sur_refl*1.stats', AQUA_SATELLITE_NAME)]

# MODIS band 2 maps to Landsat band 4
NIR_SENSOR_INFO = [('lndsr.LT4*band4.stats', L4_SATELLITE_NAME),
                   ('lndsr.LT5*band4.stats', L5_SATELLITE_NAME),
                   ('lndsr.LE7*band4.stats', L7_SATELLITE_NAME),
                   ('MOD*sur_refl*2.stats', TERRA_SATELLITE_NAME),
                   ('MYD*sur_refl*2.stats', AQUA_SATELLITE_NAME)]

# Only MODIS band 20 files
EMIS_20_SENSOR_INFO = [('MOD*Emis_20.stats', TERRA_SATELLITE_NAME),
                       ('MYD*Emis_20.stats', AQUA_SATELLITE_NAME)]

# Only MODIS band 22 files
EMIS_22_SENSOR_INFO = [('MOD*Emis_22.stats', TERRA_SATELLITE_NAME),
                       ('MYD*Emis_22.stats', AQUA_SATELLITE_NAME)]

# Only MODIS band 23 files
EMIS_23_SENSOR_INFO = [('MOD*Emis_23.stats', TERRA_SATELLITE_NAME),
                       ('MYD*Emis_23.stats', AQUA_SATELLITE_NAME)]

# Only MODIS band 29 files
EMIS_29_SENSOR_INFO = [('MOD*Emis_29.stats', TERRA_SATELLITE_NAME),
                       ('MYD*Emis_29.stats', AQUA_SATELLITE_NAME)]

# Only MODIS band 31 files
EMIS_31_SENSOR_INFO = [('MOD*Emis_31.stats', TERRA_SATELLITE_NAME),
                       ('MYD*Emis_31.stats', AQUA_SATELLITE_NAME)]

# Only MODIS band 32 files
EMIS_32_SENSOR_INFO = [('MOD*Emis_32.stats', TERRA_SATELLITE_NAME),
                       ('MYD*Emis_32.stats', AQUA_SATELLITE_NAME)]

# Only MODIS Day files
LST_DAY_SENSOR_INFO = [('MOD*LST_Day_*.stats', TERRA_SATELLITE_NAME),
                       ('MYD*LST_Day_*.stats', AQUA_SATELLITE_NAME)]

# Only MODIS Night files
LST_NIGHT_SENSOR_INFO = [('MOD*LST_Night_*.stats', TERRA_SATELLITE_NAME),
                         ('MYD*LST_Night_*.stats', AQUA_SATELLITE_NAME)]

# MODIS and Landsat files
NDVI_SENSOR_INFO = [('lndsr.LT4*-NDVI.stats', L4_SATELLITE_NAME),
                    ('lndsr.LT5*-NDVI.stats', L5_SATELLITE_NAME),
                    ('lndsr.LE7*-NDVI.stats', L7_SATELLITE_NAME),
                    ('MOD*_NDVI.stats', TERRA_SATELLITE_NAME),
                    ('MYD*_NDVI.stats', AQUA_SATELLITE_NAME)]

# MODIS and Landsat files
EVI_SENSOR_INFO = [('lndsr.LT4*-EVI.stats', L4_SATELLITE_NAME),
                   ('lndsr.LT5*-EVI.stats', L5_SATELLITE_NAME),
                   ('lndsr.LE7*-EVI.stats', L7_SATELLITE_NAME),
                   ('MOD*_EVI.stats', TERRA_SATELLITE_NAME),
                   ('MYD*_EVI.stats', AQUA_SATELLITE_NAME)]

# Only Landsat SAVI files
SAVI_SENSOR_INFO = [('lndsr.LT4*-SAVI.stats', L4_SATELLITE_NAME),
                    ('lndsr.LT5*-SAVI.stats', L5_SATELLITE_NAME),
                    ('lndsr.LE7*-SAVI.stats', L7_SATELLITE_NAME)]

# Only Landsat MSAVI files
MSAVI_SENSOR_INFO = [('lndsr.LT4*-MSAVI.stats', L4_SATELLITE_NAME),
                     ('lndsr.LT5*-MSAVI.stats', L5_SATELLITE_NAME),
                     ('lndsr.LE7*-MSAVI.stats', L7_SATELLITE_NAME)]

# Only Landsat NBR files
NBR_SENSOR_INFO = [('lndsr.LT4*-nbr.stats', L4_SATELLITE_NAME),
                   ('lndsr.LT5*-nbr.stats', L5_SATELLITE_NAME),
                   ('lndsr.LE7*-nbr.stats', L7_SATELLITE_NAME)]

# Only Landsat NBR2 files
NBR2_SENSOR_INFO = [('lndsr.LT4*-nbr2.stats', L4_SATELLITE_NAME),
                    ('lndsr.LT5*-nbr2.stats', L5_SATELLITE_NAME),
                    ('lndsr.LE7*-nbr2.stats', L7_SATELLITE_NAME)]

# Only Landsat NDMI files
NDMI_SENSOR_INFO = [('lndsr.LT4*-ndmi.stats', L4_SATELLITE_NAME),
                    ('lndsr.LT5*-ndmi.stats', L5_SATELLITE_NAME),
                    ('lndsr.LE7*-ndmi.stats', L7_SATELLITE_NAME)]
##############################################################################


#=============================================================================
def process_stats():
    '''
    Description:
      Process the stat results to plots.  If any bands/files do not exist,
      plots will not be generated for them.
    '''

    #---------------------------------------------------------------------
    process_band_type(BLUE_SENSOR_INFO, "SR Blue")
    process_band_type(GREEN_SENSOR_INFO, "SR Green")
    process_band_type(RED_SENSOR_INFO, "SR Red")
    process_band_type(NIR_SENSOR_INFO, "SR NIR")
    process_band_type(SWIR1_SENSOR_INFO, "SR SWIR1")
    process_band_type(SWIR2_SENSOR_INFO, "SR SWIR2")

    #---------------------------------------------------------------------
    process_band_type(THERMAL_SENSOR_INFO, "SR Thermal")

    #---------------------------------------------------------------------
    process_band_type(SWIR_MODIS_B5_SENSOR_INFO, "SR SWIR B5")

    #---------------------------------------------------------------------
    process_band_type(EMIS_20_SENSOR_INFO, "Emis Band 20")
    process_band_type(EMIS_22_SENSOR_INFO, "Emis Band 22")
    process_band_type(EMIS_23_SENSOR_INFO, "Emis Band 23")
    process_band_type(EMIS_29_SENSOR_INFO, "Emis Band 29")
    process_band_type(EMIS_31_SENSOR_INFO, "Emis Band 31")
    process_band_type(EMIS_32_SENSOR_INFO, "Emis Band 32")

    #---------------------------------------------------------------------
    process_band_type(LST_DAY_SENSOR_INFO, "LST Day")
    process_band_type(LST_NIGHT_SENSOR_INFO, "LST Night")

    #---------------------------------------------------------------------
    process_band_type(NDVI_SENSOR_INFO, "NDVI")

    #---------------------------------------------------------------------
    process_band_type(EVI_SENSOR_INFO, "EVI")

    #---------------------------------------------------------------------
    process_band_type(SAVI_SENSOR_INFO, "SAVI")

    #---------------------------------------------------------------------
    process_band_type(MSAVI_SENSOR_INFO, "MSAVI")

    #---------------------------------------------------------------------
    process_band_type(NBR_SENSOR_INFO, "NBR")

    #---------------------------------------------------------------------
    process_band_type(NBR2_SENSOR_INFO, "NBR2")

    #---------------------------------------------------------------------
    process_band_type(NDMI_SENSOR_INFO, "NDMI")

# END - process_stats


#=============================================================================
def process(args):
    '''
    Description:
      Retrieves the stats directory from the specified location.
      Calls process_stats to generate the plots and combined stats files.
    '''

    local_work_directory = 'lpvs_statistics'
    remote_stats_directory = args.order_directory + '/stats'
    remote_location = args.source_host + ':' + remote_stats_directory

    # Make sure the directory does not exist
    shutil.rmtree(local_work_directory, ignore_errors=True)

    cmd = ['scp', '-q', '-o', 'StrictHostKeyChecking=no', '-c', 'arcfour',
           '-C', '-r', remote_location, local_work_directory]
    cmd = ' '.join(cmd)
    try:
        output = execute_cmd(cmd)
    except Exception, e:
        log ("Failed retrieving stats from online cache")
        log (output)
        raise Exception (str(e)), None, sys.exc_info()[2]

    # Change to the statistics directory
    current_directory = os.getcwd()
    os.chdir(local_work_directory)

    try:
        process_stats()

        # Distribute back to the online cache
        lpvs_files = '*'
        remote_lpvs_directory = '%s/%s' \
            % (args.order_directory, local_work_directory)
        log ("Creating lpvs_statistics directory %s on %s" \
            % (remote_lpvs_directory, args.source_host))
        cmd = ['ssh', '-q', '-o', 'StrictHostKeyChecking=no', args.source_host,
               'mkdir', '-p', remote_lpvs_directory]
        cmd = ' '.join(cmd)
        output = ''
        try:
            output = execute_cmd (cmd)
        except Exception, e:
            log (output)
            raise Exception (str(e)), None, sys.exc_info()[2]

        # Transfer the lpvs plot and statistic files
        scp_transfer_file('localhost', lpvs_files, args.source_host,
            remote_lpvs_directory)

        log ("Verifying statistics transfers")
        # NOTE - Re-purposing the lpvs_files variable
        lpvs_files = glob.glob(lpvs_files)
        for file in lpvs_files:
            local_cksum_value = 'a b c'
            remote_cksum_value = 'b c d'

            # Generate a local checksum value
            cmd = ['cksum', file]
            cmd = ' '.join(cmd)
            try:
                local_cksum_value = execute_cmd (cmd)
            except Exception, e:
                log (local_cksum_value)
                raise Exception (str(e)), None, sys.exc_info()[2]

            # Generate a remote checksum value
            remote_file = remote_lpvs_directory + '/' + file
            cmd = ['ssh', '-q', '-o', 'StrictHostKeyChecking=no',
                args.source_host, 'cksum', remote_file]
            cmd = ' '.join(cmd)
            try:
                remote_cksum_value = execute_cmd (cmd)
            except Exception, e:
                log (remote_cksum_value)
                raise Exception (str(e)), None, sys.exc_info()[2]

            # Checksum validation
            if local_cksum_value.split()[0] != remote_cksum_value.split()[0]:
                raise Exception (
                    "Failed checksum validation between %s and %s:%s" \
                        % (file, args.source_host, remote_file))
    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
        # Remove the local_work_directory
        if not args.keep:
            shutil.rmtree(local_work_directory)

    log ("Plot Processing Complete")
# END - process


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

    # Setup debug
    set_debug (args.debug)

    try:
        # Call the main processing routine
        process (args)
    except Exception, e:
        log ("Error: %s" % str(e))
        tb = traceback.format_exc()
        log ("Traceback: [%s]" % tb)
        if hasattr(e, 'output'):
            log ("Error: Output [%s]" % e.output)
        sys.exit (EXIT_FAILURE)

    sys.exit (EXIT_SUCCESS)

