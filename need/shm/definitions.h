#ifndef DEFINITIONS_H
#define DEFINITIONS_H


#define BUFFER_LENGTH 4096
#define BUFFER_START 0
#define MAX_BUFFERS 20

#define MASTER_BUFFER_NAME "manager_buffer"
#define ENFORCER_BUFFER "enforcer_buffer_%d"


#define LOGFILE "/tmp/example.log"

#define ID_ACQUISITION_MUTEX_NAME "/id_acquisition_mutex"
#define READ_CHANGES_MUTEX_NAME "/read_changes_mutex"
#define WRITE_CHANGES_MUTEX_NAME "/write_changes_mutex"
#define SEM_BUFFER_COUNT_NAME "/sem-buffer-count"
#define SEM_SPOOL_SIGNAL_NAME "/sem-spool-signal"
#define SHARED_MEM_NAME "/posix-shared-mem-example"


#define manager (master->manager_elem)
#define enforcer(i) (master->enforcers[i])



#endif