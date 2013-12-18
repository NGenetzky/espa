
# espa-common objects and methods
from espa_constants import *

program_exit_code = EXIT_SUCCESS

exit_success              =  EXIT_SUCCESS
exit_failure              =  EXIT_FAILURE
environment               =  2
creating_staging_dir      =  3
creating_working_dir      =  4
creating_output_dir       =  5
file_transfer             =  6
unpacking                 =  7
ledaps                    =  8
sr_browse                 =  9
spectral_indices          = 10
solr                      = 11
cfmask                    = 12
cfmask_append             = 13
warping                   = 14
purging                   = 15
packaging_distribution    = 16
cleanup_work_dir          = 17
dem                       = 18
swe                       = 19
sca                       = 20
metadata                  = 21

def set_program_exit_code (exit_code):
    program_exit_code = exit_code

def get_program_exit_code():
    return program_exit_code

# END class cdr_ecv_exit_codes

