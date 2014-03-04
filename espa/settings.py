
# cdr_ecv_cron.py ============================================================

# Specify the buffer length for an order line in the order file.
order_buffer_length = 2048

# Define the hadoop timeouts to a ridiculous number so the jobs don't get
# killed before they are done.
hadoop_timeout = 172800000 # which is 2 days


# cdr_ecv.py =================================================================

# Default paths to the source and output data locations.
base_source_path = '/data/standard_l1t' # OLD NAME
landsat_base_source_path = '/data/standard_l1t' # NEW NAME

base_output_path = '/data2/LSRD' # OLD NAME
espa_base_output_path = '/data2/LSRD' # NEW NAME


# modis.py ===================================================================
base_source_path = '/MOLT' # OLD NAME
base_source_path = '/MOLA' # OR OLD NAME
terra_base_source_path = '/MOLT' # NEW NAME
aqua_base_source_path = '/MOLA' # NEW NAME

# SEE ABOVE DUPLICATED
base_output_path = '/data2/LSRD' # OLD NAME
espa_base_output_path = '/data2/LSRD' # NEW NAME


# lpvs_cron.py ===============================================================
espa_cache_directory = '/data2/LSRD' # or from env[DEV_CACHE_DIRECTORY]


# browse.py ==================================================================

# Default resolution for browse generation
default_resolution = 50 # OLD NAME
default_browse_resolution = 50 # NEW NAME


# science.py =================================================================
# SEE ABOVE DUPLICATED
default_browse_resolution = 50

default_solr_collection_name = 'DEFAULT_COLLECTION'


# distribution.py ============================================================

# The number of seconds to sleep when errors are encountered before attempting
# the task again.
default_sleep_seconds = 2

# The maximum number of times to attempt a transfer.
max_number_of_attempts = 3


# util.py ====================================================================

#140 is here twice so the load is 2/3 + 1/3.  machines are mismatched
hostlist = ['edclxs67p', 'edclxs140p', 'edclxs140p'] # OLD NAME
cache_host_list = ['edclxs67p', 'edclxs140p', 'edclxs140p'] # NEW NAME

