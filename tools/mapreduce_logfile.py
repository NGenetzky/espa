#!/usr/bin/env python
'''****************************************************************************
FILE:

PURPOSE:

PROJECT: Land Satellites Data System Science Research and Development (LSRD)
    at the USGS EROS

LICENSE TYPE: NASA Open Source Agreement Version 1.3

AUTHOR: ngenetzky@usgs.gov


****************************************************************************'''
import sys
import datetime
'''
        Helper Functions
'''
lines_that_failed_to_parse = []


def write_parse_failed_logs(outfile):
    with open(outfile, 'w+') as fp:
        for line in lines_that_failed_to_parse:
            fp.write(str(line))


def fail_to_parse(value, line):
    lines_that_failed_to_parse.append('Failed to parse for {0} in <{1}>'
                                      .format(value, line))
    return 'BAD_PARSE'


def substring_between(s, start, finish):
    '''Find string between two substrings'''
    end_of_start = s.index(start) + len(start)
    start_of_finish = s.index(finish, end_of_start)
    return s[end_of_start:start_of_finish]


def sort_ascending_by_value(unsorted_truples, reverse=False):
    return sorted(unsorted_truples,
                  key=lambda (k, v): v,  # sort by value
                  reverse=reverse)


def sort_dict_by_value(unsorted_dict, reverse=False):
    return sorted(unsorted_dict.iteritems(),
                  key=lambda (k, v): v,
                  reverse=reverse)

'''
        Extract Data from line in logfile
'''


def get_rtcode(line):
    '''Obtain a return_code from a line of text

    Precondition: line is a ' ' separated list of data.
                Return code is the first int in the items from 6 to 11.
    Postcondition: return return_code
    '''
    data = line.split()
    if(data[8].isdigit()):
        return data[8]
    else:
        return fail_to_parse('rtcode', line)


def get_bytes(line):
    '''Obtain a return_code from a line of text

    Precondition: line is a ' ' separated list of data.
                Bytes downloaded is the second int in the items from 6 to 12.
    Postcondition: return bytes_downloaded
    '''
    data = line.split()
    if(data[9].isdigit()):
        return data[9]
    else:
        return fail_to_parse('bytes', line)


def get_datetime(line):
    time_local = substring_between(line, '[', '] "')
    return datetime.datetime.strptime(time_local,
                                      '%d/%b/%Y:%H:%M:%S -0500')


def get_date(line):
    try:
        return get_datetime(line).date()
    except ValueError:
        return fail_to_parse('date', line)


def get_user_email(line):
    try:
        return substring_between(line, 'orders/', '-')
    except ValueError:
        return fail_to_parse('datetime', line)


def get_scene_id(line):
    try:
        return substring_between(line, '/', '.tar.gz')
    except ValueError:
        try:
            return substring_between(line, '/', '.cksum')
        except ValueError:
            return fail_to_parse('sceneid', line)

'''
        Filter helper functions
'''


def is_successful_request(line):
    return (get_rtcode(line) in ['200', '206'])


def is_404_request(line):
    return (get_rtcode(line) in ['404'])


def is_aborted_request(line):
    return (get_rtcode(line) in ['499', '304'])


def is_production_order(line):
    return ('"GET /orders/' in line)


def is_dswe_order(line):
    return (('"GET /provisional/dswe/' in line) or
            ('"GET /downloads/provisional/dswe/' in line))


def is_burned_area_order(line):
    return (('"GET /provisional/burned_area/' in line) or
            ('"GET /downloads/provisional/burned_area/' in line))

'''
        Mappers
'''


def map_line_to_custom_truple(line):
    ''' Obtain (return_code, bytes_downloaded) from a line of text

    Precondition: line is a ' ' separated list of data.
                Return code is the first int in the items from 6 to 11.
                Bytes downloaded is the second int in the items from 6 to 12.
    Postcondition: return list where len(list)==2
                    list[0] is return_code
                    list[1] is bytes_downloaded
                    fail_to_parse('date', line)
    '''
    remote_addr = line.split(' - ', 1)[0]
    dt = get_datetime(line).isoformat()
    request = substring_between(line, '] "', '" ')
    user_email = get_user_email(line)
    bytes_sent = get_bytes(line)
    try:
        orderid = substring_between(request, 'orders/', '/')
    except ValueError:
        orderid = fail_to_parse('orderid', line)
    sceneid = get_scene_id(line)
    return (dt, remote_addr, user_email, orderid, sceneid, bytes_sent)


def map_line_to_rtcode_bytes(line):
    ''' Obtain (return_code, bytes_downloaded) from a line of text

    Precondition: line is a ' ' separated list of data.
                Return code is the first int in the items from 6 to 11.
                Bytes downloaded is the second int in the items from 6 to 12.
    Postcondition: return list where len(list)==2
                    list[0] is return_code
                    list[1] is bytes_downloaded
    '''
    # print('MAP<{0}>'.format(line))
    return (get_rtcode(line), int(get_bytes(line)))


def map_line_to_email_date(line):
    ''' Obtain (user_email, datetime_isoformat) from a line of text

    Precondition: line is a ' ' separated list of data.
        Between the first '[', and '] "' there exists the date similar
            to "07/Jun/2015"
        data[6] contains the user's request
        The user email is contained between "orders/" and the next "-"
    Postcondition: truple is returned in the form (user_email, datetime)
        datetime will be in isoformat, similar to "2015-07-27"
    '''
    return (get_user_email(line), get_date(line).isoformat())


'''
        Reducers
'''


def reduce_flatten_to_csv(accum, next_truple):
    if accum is None:
        accum = []
    accum.append(','.join(next_truple))
    return accum


def reduce_append_value_to_key_list(accum_list, next_truple):
    '''Appends value to existing value of accum_list[key]

    Used by reduce to create list of values within dict with identical keys
    Precondition:
        next_truple  has attribute '__getitem__'
        next_truple[0] is key, next_truple[1] is value
        accum_list is dictionary
    Postcondition:
        returns a version of accum_list which either contains
            a new key/value or with a single key having a modified value.
    '''
    if next_truple is None:
        return accum_list
    try:
        accum_list[next_truple[0]].append(next_truple[1])
    except KeyError:
        accum_list[next_truple[0]] = []
        accum_list[next_truple[0]].append(next_truple[1])
    return accum_list


def reduce_accum_value_per_key(accum, next_truple):
    '''Adds value to existing value of accum[key]

    Used by reduce to accumulate values within dict with identical keys
    Precondition:
        next_truple  has attribute '__getitem__'
        next_truple[0] is key, next_truple[1] is value
        accum_bytes_per_code is dictionary
    Postcondition:
        returns a version of accum which either contains
            a new key/value or with a single key having a modified value.
    '''
    if next_truple is None:
        return accum
    try:
        accum[next_truple[0]] += next_truple[1]
    except KeyError:
        accum[next_truple[0]] = next_truple[1]
    return accum


def reduce_count_occurances_per_key(count, next_truple):
    '''Adds 1 to existing value of count[key]

    Used by reduce to count occurances of key
    Precondition:
        next_truple  has attribute '__getitem__'
        next_truple[0] is key, next_truple[1] is value
        count is dictionary
    Postcondition:
        returns a version of count which either contains
            a new key/value or with a single key having a modified value.
    '''
    if next_truple is None:
        return count
    try:
        count[next_truple[0]] += 1
    except KeyError:
        count[next_truple[0]] = 1
    return count


def reduce_count_per_keyvalue_occurances(count, next_truple):
    '''Adds 1 to existing value of count[(key,value)]

    Used by reduce to count occurances of key
    Precondition:
        next_truple  has attribute '__getitem__'
        next_truple[0] is key, next_truple[1] is value
        count is dictionary
    Postcondition:
        returns a version of count which either contains
            a new key/value or with a single key having a modified value.
    '''
    if next_truple is None:
        return count
    try:
        count[(next_truple[0], next_truple[1])] += 1
    except KeyError:
        count[(next_truple[0], next_truple[1])] = 1
    return count

'''
        Mapreduce
'''


def mapreduce_csv(iterable):
    truples = map(map_line_to_custom_truple, iterable)
    return reduce(reduce_flatten_to_csv, truples, [])


def mapreduce_total_bytes(iterable):
    list_of_bytes = map(get_bytes, iterable)
    return reduce(lambda total, x: int(total)+int(x), list_of_bytes)


def mapreduce_total_occurances(iterable):
    '''Basically len(iterable)'''
    list_of_bytes = map(lambda x: 1, iterable)
    return reduce(lambda total, x: int(total)+1, list_of_bytes)


def mapreduce_bytes_per_code(iterable):
    '''Extracts return_code and downloaded_bytes then accumulates bytes per code

    Description:
        generate iterable of lists containing [return_code, downloaded_bytes]
        then all downloaded_bytes with the same return_code are accumulated and
        the answer is returned
    Precondition:
        iterable contains strings
    Postcondition:
        return bytes_per_code, a dictionary
        bytes_per_code contains return_code (key) and downloaded_bytes (value)
    '''
    bytes_per_code = {}
    code_bytes = map(map_line_to_rtcode_bytes, iterable)
    return reduce(reduce_accum_value_per_key, code_bytes, bytes_per_code)


def mapreduce_occurances_per_code(iterable):
    '''Extracts return_code and downloaded_bytes then accumulates bytes per code

    Description:
        generate iterable of lists containing [return_code, downloaded_bytes]
        then the occurrences of return_code are counted and returned
    Precondition:
        iterable contains strings
    Postcondition:
        return occurances_per_code, a dictionary
        occurances_per_code contains return_code (key) and occurances (value)
    '''
    occurances_per_code = {}
    code_bytes = map(map_line_to_rtcode_bytes, iterable)
    return reduce(reduce_count_occurances_per_key,
                  code_bytes, occurances_per_code)


def mapreduce_occurances_per_email(iterable):
    occurances_per_email = {}
    email_date = map(map_line_to_email_date, iterable)
    return reduce(reduce_count_occurances_per_key,
                  email_date, occurances_per_email)


def mapreduce_list_dates_per_email(iterable):
    list_per_email = {}
    email_date = map(map_line_to_email_date, iterable)
    return reduce(reduce_append_value_to_key_list,
                  email_date, list_per_email)


def mapreduce_occurances_per_email_date(iterable):
    occurances_per_email_date = {}
    email_date = map(map_line_to_email_date, iterable)
    return reduce(reduce_count_per_keyvalue_occurances,
                  email_date, occurances_per_email_date)
'''
        Reports - Combine filters with mapreduce
'''


def report_succuessful_production_bytes(iterable):
    only_production = filter(is_production_order, iterable)
    only_successful_production = filter(is_successful_request,
                                        only_production)
    return str(mapreduce_total_bytes(only_successful_production))


def report_succuessful_dswe_bytes(iterable):
    only_dswe = filter(is_dswe_order, iterable)
    only_successful_dswe = filter(is_successful_request,
                                  only_dswe)
    return str(mapreduce_total_bytes(only_successful_dswe))


def report_succuessful_burned_area_bytes(iterable):
    only_burned_area = filter(is_burned_area_order, iterable)
    only_successful_burned_area = filter(is_successful_request,
                                         only_burned_area)
    return str(mapreduce_total_bytes(only_successful_burned_area))


def report_succuessful_production_requests(iterable):
    only_production = filter(is_production_order, iterable)
    only_successful_production = filter(is_successful_request,
                                        only_production)
    return str(mapreduce_total_occurances(only_successful_production))


def report_succuessful_dswe_requests(iterable):
    only_dswe = filter(is_dswe_order, iterable)
    only_successful_dswe = filter(is_successful_request,
                                  only_dswe)
    return str(mapreduce_total_occurances(only_successful_dswe))


def report_succuessful_burned_area_requests(iterable):
    only_burned_area = filter(is_burned_area_order, iterable)
    only_successful_burned_area = filter(is_successful_request,
                                         only_burned_area)
    return str(mapreduce_total_occurances(only_successful_burned_area))


def report_404_per_user_email_on_production_orders(iterable):
    ''' Will compile a report that provides total offenses per user

    Precondition: offenses_per_email is a dict
        Key is user_emails and Value is list of dates that offenses occurred
    Postcondition: returns string of each each user_report separated by '\n'
        Each user_report contains total_offenses and user_email
        Report is sorted from most offenses to least offenses
    '''
    only_production = filter(is_production_order, iterable)
    production_404requests = filter(is_404_request, only_production)
    offenses_per_email = mapreduce_occurances_per_email(production_404requests)

    sorted_num_of_offenses = sort_dict_by_value(offenses_per_email,
                                                reverse=True)

    final_report = []
    for item in sorted_num_of_offenses:
        # item[0] = email, item[1] = number of offenses
        final_report.append('{1} {0}'.format(item[0], item[1]))

    return '\n'.join(final_report)


def report_404_per_email_date_on_production_orders(iterable):
    ''' Will compile a report that provides total offenses per user

    Precondition: offenses_per_email is a dict
        Key is user_emails and Value is list of dates that offenses occurred
    Postcondition: returns string of each each user_report separated by '\n'
        Each user_report contains total_offenses and user_email
        Report is sorted from most offenses to least offenses
    '''
    only_production = filter(is_production_order, iterable)
    production_404req = filter(is_404_request, only_production)

    offenses_per_email = mapreduce_occurances_per_email_date(production_404req)

    sorted_num_of_offenses = sort_dict_by_value(offenses_per_email,
                                                reverse=True)

    final_report = []
    for item in sorted_num_of_offenses:
        # item[0] = email, item[1] = number of offenses
        final_report.append('{1} {0}'.format(item[0], str(item[1])))

    return '\n'.join(final_report)


def report_email_offense_list(iterable):
    ''' Will compile a report that provides total & perday offenses per user

    Precondition: offenses_per_email is a dict
        Key is user_emails and Value is list of dates that offenses occurred
    Postcondition: returns string of each each user_report separated by '\n'
        Each user_report contains total_offenses and user_email on first line
            the following lines contain a date and the offenses on that date
    '''
    only_404req = filter(is_404_request, iterable)
    offenses_per_email_date = mapreduce_occurances_per_email_date(only_404req)

    sorted_num_of_offenses = sort_dict_by_value(offenses_per_email_date,
                                                reverse=True)
    final_report = []
    for item in sorted_num_of_offenses:
        # item[0] = email, item[1] = number of offenses
        final_report.append('{1} {0}'.format(str(item[0]), item[1]))

    return '\n'.join(final_report)


def report_csv_of_successful_orders(iterable):
    only_production = filter(is_production_order, iterable)
    only_successful_production = filter(is_successful_request,
                                        only_production)
    return '\n'.join(mapreduce_csv(only_successful_production))
'''
        Access a report by running script
'''


def main(iterable):
    report_csv_of_successful_orders(iterable)
    write_parse_failed_logs('lines_not_parsed.txt')


if __name__ == '__main__':
    print(main(iterable=sys.stdin.readlines()))


