#ifndef DEFINITIONS_H
#define DEFINITIONS_H


#define BUFFER_LENGTH   4096
#define BUFFER_START    0
#define MAX_BUFFERS     2
//#define MAX_ENFORCERS   911     // keep it a prime number
#define MAX_ENFORCERS   17     // keep it a prime number

#define MASTER_BUFFER_NAME  "manager_buffer"
#define ENFORCER_BUFFER     "enforcer_buffer_%d"


#define LOGFILE "/tmp/example.log"

#define ID_ACQUISITION_MUTEX_NAME   "/id_acquisition_mutex"
#define READ_CHANGES_MUTEX_NAME     "/read_changes_mutex"
#define WRITE_CHANGES_MUTEX_NAME    "/write_changes_mutex"
#define SEM_BUFFER_COUNT_NAME       "/sem-buffer-count"
#define SEM_SPOOL_SIGNAL_NAME       "/sem-spool-signal"
#define SHARED_MEM_NAME             "/posix-shared-mem-example"


#define manager                 (master->manager_elem)
//#define manager_r_buffer        (master->manager_elem.buffer[master->manager_elem.read_buffer])
//#define manager_w_buffer        (master->manager_elem.buffer[master->manager_elem.write_buffer])

#define enforcer(i)             (master->enforcers[i])
#define enforcer_flows_buff(i)    (master->enforcers[i].flows_buffer)
#define enforcer_changes_buff(i)    (master->enforcers[i].changes_buffer)



#endif