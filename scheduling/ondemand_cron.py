#! /usr/bin/env python

'''
    FILE: ondemand_cron.py

    PURPOSE: Master script for new Hadoop jobs.  Queries the xmlrpc
             service to find requests that need to be processed and
             builds/executes a Hadoop job to process them.

    PROJECT: Land Satellites Data Systems Science Research and Development
             (LSRD) at the USGS EROS

    LICENSE: NASA Open Source Agreement 1.3

    HISTORY:

    Date              Programmer               Reason
    ----------------  ------------------------ -------------------------------
    09/12/2013        David V. Hill            Initial implementation
    Jan/2014          Ron Dilley               Updated for recent processing
                                               enhancements.
    Sept/2014         Ron Dilley               Updated to use espa_common and
                                               our python logging setup
    Oct/2014          Ron Dilley               Renamed and incorporates all of
                                               our ondemand cron processing
'''

import os
import sys
import json
import xmlrpclib
import urllib
from datetime import datetime
from argparse import ArgumentParser

# espa-common objects and methods
from espa_constants import EXIT_FAILURE
from espa_constants import EXIT_SUCCESS

# imports from espa/espa_common
from espa_common import settings, utilities
from espa_common.logger_factory import EspaLogging as EspaLogging


# ============================================================================
def process_requests(args, logger_name, queue_priority, request_priority):
    '''
    Description:
      Queries the xmlrpc service to see if there are any requests that need
      to be processed with the specified type, priority and/or user.  If there
      are, this method builds and executes a hadoop job and updates the status
      for each request through the xmlrpc service."
    '''

    # Get the logger for this task
    logger = EspaLogging.get_logger(logger_name)

    rpcurl = os.environ.get('ESPA_XMLRPC')
    server = None

    # Create a server object if the rpcurl seems valid
    if (rpcurl is not None and rpcurl.startswith('http://')
            and len(rpcurl) > 7):

        server = xmlrpclib.ServerProxy(rpcurl, allow_none=True)
    else:
        raise Exception("Missing or invalid environment variable ESPA_XMLRPC")

    home_dir = os.environ.get('HOME')
    hadoop_executable = "%s/bin/hadoop/bin/hadoop" % home_dir

    # Verify xmlrpc server
    if server is None:
        msg = "xmlrpc server was None... exiting"
        raise Exception(msg)

    user = server.get_configuration('landsatds.username')
    if len(user) == 0:
        msg = "landsatds.username is not defined... exiting"
        raise Exception(msg)

    pw = urllib.quote(server.get_configuration('landsatds.password'))
    if len(pw) == 0:
        msg = "landsatds.password is not defined... exiting"
        raise Exception(msg)

    host = server.get_configuration('landsatds.host')
    if len(host) == 0:
        msg = "landsatds.host is not defined... exiting"
        raise Exception(msg)

    # Use ondemand_enabled to determine if we should be processing or not
    ondemand_enabled = server.get_configuration('ondemand_enabled')

    # Determine the appropriate hadoop queue to use
    hadoop_job_queue = settings.HADOOP_QUEUE_MAPPING[queue_priority]

    if not ondemand_enabled.lower() == 'true':
        raise Exception("on demand disabled... exiting")

    try:
        logger.info("Checking for requests to process...")
        requests = server.get_scenes_to_process(int(args.limit), args.user,
                                                request_priority,
                                                list(args.product_types))
        if requests:
            # Figure out the name of the order file
            stamp = datetime.now()
            job_name = ('%s_%s_%s_%s_%s_%s-%s-espa_job'
                        % (str(stamp.month), str(stamp.day),
                           str(stamp.year), str(stamp.hour),
                           str(stamp.minute), str(stamp.second),
                           str(queue_priority)))

            logger.info(' '.join(["Found requests to process,",
                                  "generating job name:", job_name]))

            job_filename = '%s%s' % (job_name, '.txt')
            job_filepath = os.path.join('/tmp', job_filename)

            # Create the order file full of all the scenes requested
            with open(job_filepath, 'w+') as espa_fd:
                for request in requests:
                    (orderid, options) = (request['orderid'],
                                          request['options'])

                    request['xmlrpcurl'] = rpcurl

                    # Log the requested options before passwords are added
                    line_entry = json.dumps(request)
                    logger.info(line_entry)

                    # Add the usernames and passwords to the options
                    options['source_username'] = user
                    options['destination_username'] = user
                    options['source_pw'] = pw
                    options['destination_pw'] = pw

                    request['options'] = options

                    # Need to refresh since we added password stuff that
                    # could not be logged
                    line_entry = json.dumps(request)

                    # Pad the entry so hadoop will properly split the jobs
                    #filler_count = (settings.ORDER_BUFFER_LENGTH -
                    #                len(line_entry))
                    #request_line = ''.join([line_entry,
                    #                        ('#' * filler_count), '\n'])
                    request_line = ''.join([line_entry, '\n'])

                    # Write out the request line
                    espa_fd.write(request_line)
                # END - for scene
            # END - with espa_fd

            # Specify the location of the order file on the hdfs
            hdfs_target = 'requests/%s' % job_filename

            # Specify the mapper application
            mapper = "ondemand_mapper.py"

            # Define command line to store the job file in hdfs
            hadoop_store_command = [hadoop_executable, 'dfs', '-copyFromLocal',
                                    job_filepath, hdfs_target]

            jars = os.path.join(home_dir, 'bin/hadoop/contrib/streaming',
                                'hadoop-streaming*.jar')
            # Define command line to execute the hadoop job
            # Be careful it is possible to have conflicts between module names
            hadoop_run_command = \
                [hadoop_executable, 'jar', jars,
                 '-D', 'mapred.task.timeout=%s' % settings.HADOOP_TIMEOUT,
                 '-D', 'mapred.reduce.tasks=0',
                 '-D', 'mapred.job.queue.name=%s' % hadoop_job_queue,
                 '-D', 'mapred.job.name="%s"' % job_name,
                 '-inputformat', 'org.apache.hadoop.mapred.lib.NLineInputFormat',
                 '-file', '%s/espa-site/processing/%s' % (home_dir, mapper),
                 '-file', '%s/espa-site/processing/processor.py' % home_dir,
                 '-file', '%s/espa-site/processing/browse.py' % home_dir,
                 '-file', '%s/espa-site/processing/distribution.py' % home_dir,
                 '-file', ('%s/espa-site/processing/espa_exception.py'
                           % home_dir),
                 '-file', '%s/espa-site/processing/metadata.py' % home_dir,
                 '-file', '%s/espa-site/processing/parameters.py' % home_dir,
                 '-file', '%s/espa-site/processing/solr.py' % home_dir,
                 '-file', '%s/espa-site/processing/staging.py' % home_dir,
                 '-file', '%s/espa-site/processing/statistics.py' % home_dir,
                 '-file', '%s/espa-site/processing/environment.py' % home_dir,
                 '-file', '%s/espa-site/processing/initialization.py' % home_dir,
                 '-file', '%s/espa-site/processing/transfer.py' % home_dir,
                 '-file', '%s/espa-site/processing/warp.py' % home_dir,
                 '-file', ('%s/espa-site/espa_common/logger_factory.py'
                           % home_dir),
                 '-file', '%s/espa-site/espa_common/sensor.py' % home_dir,
                 '-file', '%s/espa-site/espa_common/settings.py' % home_dir,
                 '-file', '%s/espa-site/espa_common/utilities.py' % home_dir,
                 '-mapper', '%s/espa-site/processing/%s' % (home_dir, mapper),
                 '-cmdenv', 'ESPA_WORK_DIR=$ESPA_WORK_DIR',
                 '-cmdenv', 'HOME=$HOME',
                 '-cmdenv', 'USER=$USER',
                 '-cmdenv', 'LEDAPS_AUX_DIR=$LEDAPS_AUX_DIR',
                 '-cmdenv', 'L8_AUX_DIR=$L8_AUX_DIR',
                 '-cmdenv', 'ESUN=$ESUN',
                 '-input', hdfs_target,
                 '-output', hdfs_target + '-out']

            # Define the executables to clean up hdfs
            hadoop_delete_request_command1 = [hadoop_executable, 'dfs',
                                              '-rmr', hdfs_target]
            hadoop_delete_request_command2 = [hadoop_executable, 'dfs',
                                              '-rmr', hdfs_target + '-out']

            # ----------------------------------------------------------------
            logger.info("Storing request file to hdfs...")
            output = ''
            try:
                cmd = ' '.join(hadoop_store_command)
                logger.info("Store cmd:%s" % cmd)

                output = utilities.execute_cmd(cmd)
            except Exception, e:
                msg = "Error storing files to HDFS... exiting"
                raise Exception(msg)
            finally:
                if len(output) > 0:
                    logger.info(output)

                logger.info("Deleting local request file copy [%s]"
                            % job_filepath)
                os.unlink(job_filepath)

            try:
                # ------------------------------------------------------------
                # Update the scene list as queued so they don't get pulled
                # down again now that these jobs have been stored in hdfs
                product_list = list()
                for request in requests:
                    orderid = request['orderid']
                    sceneid = request['scene']
                    product_list.append((orderid, sceneid))

                    logger.info("Adding scene:%s orderid:%s to queued list"
                                % (sceneid, orderid))

                server.queue_products(product_list, 'CDR_ECV cron driver',
                                      job_name)

                # ------------------------------------------------------------
                logger.info("Running hadoop job...")
                output = ''
                try:
                    cmd = ' '.join(hadoop_run_command)
                    logger.info("Run cmd:%s" % cmd)

                    output = utilities.execute_cmd(cmd)
                except Exception, e:
                    logger.exception("Error running Hadoop job...")
                finally:
                    if len(output) > 0:
                        logger.info(output)

            finally:
                # ------------------------------------------------------------
                logger.info("Deleting hadoop job request file from hdfs....")
                output = ''
                try:
                    cmd = ' '.join(hadoop_delete_request_command1)
                    output = utilities.execute_cmd(cmd)
                except Exception, e:
                    logger.exception("Error deleting hadoop job request file")
                finally:
                    if len(output) > 0:
                        logger.info(output)

                # ------------------------------------------------------------
                logger.info("Deleting hadoop job output...")
                output = ''
                try:
                    cmd = ' '.join(hadoop_delete_request_command2)
                    output = utilities.execute_cmd(cmd)
                except Exception, e:
                    logger.exception("Error deleting hadoop job output")
                finally:
                    if len(output) > 0:
                        logger.info(output)

        else:
            logger.info("No requests to process....")

    except xmlrpclib.ProtocolError, e:
        logger.exception("A protocol error occurred")

    except Exception, e:
        logger.exception("Error Processing Ondemand Requests")

    finally:
        server = None
# END - process_requests


# ============================================================================
if __name__ == '__main__':
    '''
    Description:
      Execute the core processing routine.
    '''

    # Create a command line argument parser
    description = ("Builds and kicks-off hadoop jobs for the espa processing"
                   " system (to process product requests)")
    parser = ArgumentParser(description=description)

    # Add parameters
    valid_priorities = sorted(settings.HADOOP_QUEUE_MAPPING.keys())
    valid_product_types = ['landsat', 'modis', 'plot']
    parser.add_argument('--priority',
                        action='store', dest='priority', required=True,
                        choices=valid_priorities,
                        help="only process requests with this priority:"
                             " one of (%s)" % ', '.join(valid_priorities))

    parser.add_argument('--product-types',
                        action='store', dest='product_types', required=True,
                        nargs='+', metavar='PRODUCT_TYPE',
                        help=("only process requests for the specified"
                              " product type(s)"))

    parser.add_argument('--limit',
                        action='store', dest='limit', required=False,
                        default='500',
                        help="specify the max number of requests to process")

    parser.add_argument('--user',
                        action='store', dest='user', required=False,
                        default=None,
                        help="only process requests for the specified user")

    # Parse the command line arguments
    args = parser.parse_args()

    # Validate product_types
    if ((set(['landsat', 'plot']) == set(args.product_types))
            or (set(['modis', 'plot']) == set(args.product_types))
            or (set(['landsat', 'modis', 'plot']) == set(args.product_types))):
        print("Invalid --product-types: 'plot' cannot be combined with any"
              " other product types")
        sys.exit(EXIT_FAILURE)

    # Configure and get the logger for this task
    if 'plot' in args.product_types:
        logger_name = 'espa.cron.plot'
    else:
        logger_name = '.'.join(['espa.cron', args.priority.lower()])
    EspaLogging.configure(logger_name)
    logger = EspaLogging.get_logger(logger_name)

    # Check required variables that this script should fail on if they are not
    # defined
    required_vars = ['ESPA_XMLRPC', 'ESPA_WORK_DIR', 'LEDAPS_AUX_DIR',
                     'L8_AUX_DIR', 'PATH', 'HOME']
    for env_var in required_vars:
        if (env_var not in os.environ or os.environ.get(env_var) is None
                or len(os.environ.get(env_var)) < 1):

            logger.critical("$%s is not defined... exiting" % env_var)
            sys.exit(EXIT_FAILURE)

    # Determine the appropriate priority value to use for the queue and request
    queue_priority = args.priority.lower()
    request_priority = queue_priority
    if 'plot' in args.product_types:
        if queue_priority == 'all':
            # If all was specified default to high queue
            queue_priority = 'high'
        # The request priority is always None for plotting to get all of them
        request_priority = None
    else:
        if request_priority == 'all':
            # We need to use a value of None to get all of them
            request_priority = None

    # Setup and submit products to hadoop for processing
    try:
        process_requests(args, logger_name, queue_priority, request_priority)
    except Exception, e:
        logger.exception("Processing failed")
        sys.exit(EXIT_FAILURE)

    sys.exit(EXIT_SUCCESS)
