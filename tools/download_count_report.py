#!/usr/bin/env python
'''****************************************************************************
FILE: bytes_downloaded_report.py

PURPOSE: Outputs an integer that represents the number of bytes downloaded.

PROJECT: Land Satellites Data System Science Research and Development (LSRD)
    at the USGS EROS

LICENSE TYPE: NASA Open Source Agreement Version 1.3

AUTHOR: ngenetzky@usgs.gov

NOTES:

****************************************************************************'''
import sys
import mapreduce_logfile as mapred
import argparse


def parse_arguments():
    '''Parse argument, filter, default to filter='orders' '''
    desc = ('Outputs the bytes downloaded by successful requests')
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('--filter', action='store',
                        dest='filter',
                        choices=['orders', 'dswe', 'burned_area'],
                        required=False, default='orders',
                        help='Which filter criteria do you wish to use?')
    args = parser.parse_args()
    return args


def main(iterable, ordertype='orders'):
    if(ordertype not in ['orders', 'dswe', 'burned_area']):
        return ("{0} not in ordertype choices({1})"
                .format(ordertype, ['orders', 'dswe', 'burned_area']))

    if(ordertype == 'orders'):
            return mapred.report_succuessful_production_requests(iterable)
    elif(ordertype == 'burned_area'):
            return mapred.report_succuessful_burned_area_requests(iterable)
    elif(ordertype == 'dswe'):
            return mapred.report_succuessful_dswe_requests(iterable)

if __name__ == '__main__':
    args = parse_arguments()
    print(main(iterable=sys.stdin.readlines(),
               ordertype=args.filter))



