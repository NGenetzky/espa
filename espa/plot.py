#! /usr/bin/env python

import os
import sys
import glob
import datetime
import calendar
import traceback
from argparse import ArgumentParser
from collections import defaultdict
from matplotlib import pyplot as mpl_plot
from matplotlib import dates as mpl_dates

# espa-common objects and methods
from espa_constants import *
from espa_logging import log, set_debug, debug


#=============================================================================
def build_argument_parser():
    '''
    Description:
      Build the command line argument parser
    '''

    # Create a command line argument parser
    description = "Generate plots of the statics"
    parser = ArgumentParser (description=description)

    parser.add_argument ('--debug',
        action='store_true', dest='debug', default=False,
        help="turn debug logging on")

    parser.add_argument ('--stats_directory',
        action='store', dest='stats_directory', default=os.curdir,
        help="directory containing the statistics")

    parser.add_argument ('--plot_directory',
        action='store', dest='plot_directory', default=os.curdir,
        help="directory to place the plots")

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
        date_element = filename.split('.')[4]
        year = int(date_element[0:4])
        day_of_year = int(date_element[4:7])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'Terra'

    elif filename.startswith('MYD'):
        date_element = filename.split('.')[4]
        year = int(date_element[0:4])
        day_of_year = int(date_element[4:7])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'Aqua'

    elif 'LT4' in filename:
        parts = filename.split('.')
        year = int(parts[1][9:13])
        day_of_year = int(parts[1][13:16])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'LT4'

    elif 'LT5' in filename:
        parts = filename.split('.')
        year = int(parts[1][9:13])
        day_of_year = int(parts[1][13:16])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'LT5'

    elif 'LE7' in filename:
        parts = filename.split('.')
        year = int(parts[1][9:13])
        day_of_year = int(parts[1][13:16])
        (month, day_of_month) = get_mdom_from_ydoy(year, day_of_year)
        label = 'LE7'

    return (year, month, day_of_month, label)
# END - get_ymdl_from_filename


time_delta_5_days = datetime.timedelta(days=5)
#=============================================================================
def generate_plot(plot_name, subject, stats):

    auto_date_locator = mpl_dates.AutoDateLocator()
    aut_date_formatter = mpl_dates.AutoDateFormatter(auto_date_locator)

    lower_subject = subject.lower()

    # Create the subplot objects
    (fig, min_plot) = mpl_plot.subplots()

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
    for increment in range(0, int(y_diff/200) + 1):
        # Add 10 to help with the display
        plot_y_min -= 5
        plot_y_max += 5
    debug (plot_y_min)
    debug (plot_y_max)

    # Adjust the day range to help move them from the edge of the plot
    date_diff = plot_date_max - plot_date_min
    debug (date_diff.days)
    for increment in range(0, int(date_diff.days/365) + 1):
        # Add 5 more days to help with the display
        plot_date_min -= time_delta_5_days
        plot_date_max += time_delta_5_days
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
    fig.autofmt_xdate()

    # Y Axis - Limits
    min_plot.set_ylim(plot_y_min, plot_y_max)

    # Y Axis - Label
    mpl_plot.ylabel(subject)

    # Plot - Title
    plot_name += ' ' + subject
    #mpl_plot.title(plot_name)

    mpl_plot.legend(bbox_to_anchor=(0.0, 1.02, 1.0, 0.502), loc=3, ncol=5,
        mode="expand", borderaxespad=0.0, numpoints=1)

    # Fix the filename and save the plot
    filename = plot_name.replace(' ', '_').lower()
    filename += '_plot'
    mpl_plot.savefig('%s.png' % filename, dpi=96)

    # Close the plot so we can open another one
    mpl_plot.close()
# END - generate_plot


#=============================================================================
def generate_plots(plot_name, stat_files):
    '''
    Description:
      Gather all the information needed for plotting and generate a plot
    '''

    stats = dict()

    # Read each file into a dictionary
    for stat_file in stat_files:
        stats[stat_file] = \
            dict((key, value) for (key, value) in read_stats(stat_file))

    generate_plot(plot_name, 'Minimum', stats)
    generate_plot(plot_name, 'Maximum', stats)
    generate_plot(plot_name, 'Mean', stats)
    generate_plot(plot_name, 'StdDev', stats)
# END - generate_plots


#=============================================================================
def process(arguments):
    '''
    Description:
      Process the stat results to plots
    '''

    landsat_4_sr_files = dict()
    landsat_5_sr_files = dict()
    landsat_7_sr_files = dict()
    terra_sr_files = dict()
    aqua_sr_files = dict()

    # Search for bands surface reflectance bands 1-7
    for band_number in range(1,8):
        landsat_4_sr_files[band_number] = \
            glob.glob('lndsr.LT4*%d.stats' % band_number)
        landsat_5_sr_files[band_number] = \
            glob.glob('lndsr.LT5*%d.stats' % band_number)
        landsat_7_sr_files[band_number] = \
            glob.glob('lndsr.LE7*%d.stats' % band_number)
        terra_sr_files[band_number] = \
            glob.glob('MOD*sur_refl*%d.stats' % band_number)
        aqua_sr_files[band_number] = \
            glob.glob('MYD*sur_refl*%d.stats' % band_number)

    # Process through the surface reflectance bands
    for band_number in range(1,8):
        combined_stat_files = list()

        if landsat_4_sr_files and landsat_4_sr_files[band_number] != None:
            if len(landsat_4_sr_files[band_number]) > 1:
                log ("Processing landsat 4 band %d SR stats" % band_number)
                generate_plots ("Landsat 4 Band %d" % band_number,
                    landsat_4_sr_files[band_number])
            combined_stat_files += landsat_4_sr_files[band_number]

        if landsat_5_sr_files and landsat_5_sr_files[band_number] != None:
            if len(landsat_5_sr_files[band_number]) > 1:
                log ("Processing landsat 5 band %d SR stats" % band_number)
                generate_plots ("Landsat 5 Band %d" % band_number,
                    landsat_5_sr_files[band_number])
            combined_stat_files += landsat_5_sr_files[band_number]

        if landsat_7_sr_files and landsat_7_sr_files[band_number] != None:
            if len(landsat_7_sr_files[band_number]) > 1:
                log ("Processing landsat 7 band %d SR stats" % band_number)
                generate_plots ("Landsat 7 Band %d" % band_number,
                    landsat_7_sr_files[band_number])
            combined_stat_files += landsat_7_sr_files[band_number]

        if terra_sr_files and terra_sr_files[band_number] != None:
            if len(terra_sr_files[band_number]) > 1:
                log ("Processing terra band %d SR stats" % band_number)
                generate_plots ("Terra Band %d" % band_number,
                    terra_sr_files[band_number])
            combined_stat_files += terra_sr_files[band_number]

        if aqua_sr_files and aqua_sr_files[band_number] != None:
            if len(aqua_sr_files[band_number]) > 1:
                log ("Processing aqua band %d SR stats" % band_number)
                generate_plots ("Aqua Band %d" % band_number,
                    aqua_sr_files[band_number])
            combined_stat_files += aqua_sr_files[band_number]

        log ("Processing combined band %d SR stats" % band_number)
        generate_plots ("Combined Band %d" % band_number,
            combined_stat_files)

    # TODO TODO TODO TODO TODO TODO TODO TODO TODO    
    # Search for ... other product types to plot
    # Search for ... other product types to plot
    # Search for ... other product types to plot
    # Search for ... other product types to plot
    # Search for ... other product types to plot
    # TODO TODO TODO TODO TODO TODO TODO TODO TODO    

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

