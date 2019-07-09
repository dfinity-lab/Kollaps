
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
#include <semaphore.h>

#include "ManagerSharedMem.h"

#include "structures.h"
#include "definitions.h"
#include "utils.h"

/******************************************************************************************************/

void (*flowCollectorCallback)(unsigned int, unsigned int, unsigned long, unsigned int) = NULL;
void (*tearDownCallback)(int) = NULL;

unsigned int shm_master_fd;         // shared memory file descriptor
struct shm_master  *master;         // pointer to shared memory object
struct shm_semaphores semaphores;  // shared semaphores


/******************************************************************************************************/

void registerFlowCollectorCallback(void(*callback)(unsigned int src_ip, unsigned int dst_ip, unsigned long bandwidth, unsigned int qlen)) {
    flowCollectorCallback = callback;
}

void registerTearDownCallback(void(*callback)(int disableNetwork)) {
    tearDownCallback = callback;
}


/******************************************************************************************************/

void init(unsigned int numberOfEnforcers) {
    unsigned int i = 0;
    char str_buffer[64];

    // create shared memory structure
    if ((shm_master_fd = shm_open(MASTER_BUFFER_NAME, O_CREAT | O_RDWR, 0666)) == -1)
        printAndFail("[C (manager)] failed to open shm structure");

    if (ftruncate(shm_master_fd, sizeof(struct shm_master)) == -1)
        printAndFail("[C (manager)] failed to set size for shm structure");

    int protections = PROT_READ | PROT_WRITE;
    master = mmap(NULL, sizeof(struct shm_master), protections, MAP_SHARED, shm_master_fd, 0);
	if (master == MAP_FAILED)
		printAndFail("[C (manager)] mapping failed");

	// initialize structure counters and indexes
	master->enforcer_count = numberOfEnforcers;
	
    __atomic_store_n(&(master->writing_in_progress), 1, __ATOMIC_RELAXED);
	for(i = 0; i < MAX_ENFORCERS; i++) {
    	snprintf(str_buffer, 64, ENFORCER_BUFFER, i);
		if ((semaphores.enforcers[i] = sem_open(str_buffer, O_CREAT, 0660, 0)) == SEM_FAILED)
		    printAndFail("[C (manager)] failed sem_open() for enforcer_buffer_%d");
		    
        sem_post(semaphores.enforcers[i]);
        
	    enforcer(i).flows_count = 0;
	    enforcer(i).flows_idx = 0;
	    enforcer(i).changes_count = 0;
	    enforcer(i).changes_idx = 0;
	}
	
    // semaphores to control pulling of changes
	if ((semaphores.read_changes = sem_open(READ_CHANGES_MUTEX_NAME, O_CREAT, 0660, 0)) == SEM_FAILED)
		printAndFail("[C (manager)] failed sem_open() for read_changes_sem");

	if ((semaphores.write_changes = sem_open(WRITE_CHANGES_MUTEX_NAME, O_CREAT, 0660, 1)) == SEM_FAILED)
		printAndFail("[C (manager)] failed sem_open() for write_changes_sem");
		
		
    // mutual exclusion semaphore for enforcer buffer acquisition
	if ((semaphores.id_acquisition = sem_open(ID_ACQUISITION_MUTEX_NAME, O_CREAT, 0660, 0)) == SEM_FAILED)
		printAndFail("[C (manager)] failed sem_open() for id_acquisition_sem");

//    if (sem_post(semaphores.read_changes) == -1)
//		printAndFail("[C (manager)] failed sem_post() for read_changes_sem");

	// enforcers can start, set semaphore to 1
    if (sem_post(semaphores.id_acquisition) == -1)
		printAndFail("[C (manager)] failed sem_post() for id_acquisition_sem");

    printf("[C (manager)] init with %d enforcers.\n", numberOfEnforcers);
    fflush(stdout);
}


void pullFlows() {
    unsigned int i = 0, j = 0;
    unsigned int read_idx = 0;

    unsigned int dst_ip;
    unsigned long bandwidth;
    unsigned int qlen;

//    for (i = 0; i < master->enforcer_count; i++) {
    for (i = 0; i < MAX_ENFORCERS; i++) {

//        if (sem_wait(semaphores.enforcers[i]) == -1)
//		    printAndFail("[C (manager)] failed sem_wait() for enforcer_semaphore");

        read_idx = 0;
        for (j = 0; j < enforcer(i).flows_count; j++) {
            dst_ip = getUInt32(read_idx, enforcer_flows_buff(i));
            read_idx += sizeof(unsigned int);

            bandwidth = getUInt64(read_idx, enforcer_flows_buff(i));
            read_idx += sizeof(unsigned long);

            qlen = getUInt32(read_idx, enforcer_flows_buff(i));
            read_idx += sizeof(unsigned int);

            printf("[C (manager)] << newFlow %d -> %d ( %ld, %d ) from %d\n", enforcer(i).ip, dst_ip, bandwidth, qlen, i);
            (*flowCollectorCallback)(enforcer(i).ip, dst_ip, bandwidth, qlen);
        }

//        enforcer(i).flows_count = 0;
//        enforcer(i).flows_idx = 0;
        __atomic_store_n(&(enforcer(i).flows_count), 0, __ATOMIC_RELAXED);
        __atomic_store_n(&(enforcer(i).flows_idx), 0, __ATOMIC_RELAXED);

        fflush(stdout);

//        if (sem_post(semaphores.enforcers[i]) == -1)
//		    printAndFail("[C (manager)] failed sem_post() for enforcer_semaphore");
    }
}


void lock_changes() {

//    // get semaphore for buffer access
//    if (sem_wait(semaphores.read_changes) == -1)
//        printAndFail("[C (manager)] failed sem_wait() for read_changes_sem");
//
//    if (sem_wait(semaphores.write_changes) == -1)
//        printAndFail("[C (enforcer)] failed sem_wait() for write_changes_sem");

    __atomic_store_n(&(master->writing_in_progress), 1, __ATOMIC_RELAXED);

//    printf("[C (manager)] locked changes buffer.\n");
//    fflush(stdout);
}

void publishChanges() {
    __atomic_store_n(&(master->writing_in_progress), 0, __ATOMIC_RELAXED);

    int i = 0;
    for (i = 0; i <= master->enforcer_count; i++) {
        if (sem_post(semaphores.read_changes) == -1)
            printAndFail("[C (manager)] failed sem_post() for read_changes_sem");
    }

//    printf("[C (manager)] published changes and freed buffer.\n");
//    fflush(stdout);

//    int aux = manager.write_buffer;
//    manager.write_buffer = manager.read_buffer;
//    manager.read_buffer = manager.write_buffer;

//    manager.active_buffer = (manager.active_buffer + 1) % MAX_BUFFERS;



//    // finished writing, release semaphore #readers times
//    int value;
//    sem_getvalue(semaphores.read_changes, &value);
//    for (; value > 0 - master->enforcer_count; value--) {
//        printf("[C (manager)] read_changes_sem = %d.\n", value);
//        fflush(stdout);
//
//        if (sem_post(semaphores.read_changes) == -1)
//            printAndFail("[C (manager)] failed sem_post() for read_changes_sem");
//    }
}


/******************************************************************************************************/

void initDestination(unsigned int src_ip, unsigned int dst_ip, unsigned long bandwidth, float latency, float jitter, float packetLoss) {
    printf("[C (manager)] << initDestination %d -> %d ( %ld, %f, %f, %f )\n", src_ip, dst_ip, bandwidth, latency, jitter, packetLoss);
    fflush(stdout);
    
    struct shm_element *enforcer = &enforcer(src_ip % MAX_ENFORCERS);
    
    putFunction(enforcer->changes_idx, enforcer->changes_buffer, INIT_DESTINATION);
    enforcer->changes_idx += sizeof(enum function);
    
//    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, src_ip);
//    enforcer->changes_idx += sizeof(unsigned int);

    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, dst_ip);
    enforcer->changes_idx += sizeof(unsigned int);
    
    putUInt64(enforcer->changes_idx, enforcer->changes_buffer, bandwidth);
    enforcer->changes_idx += sizeof(unsigned long);
    
    putFloat(enforcer->changes_idx, enforcer->changes_buffer, latency);
    enforcer->changes_idx += sizeof(float);
    
    putFloat(enforcer->changes_idx, enforcer->changes_buffer, jitter);
    enforcer->changes_idx += sizeof(float);
    
    putFloat(enforcer->changes_idx, enforcer->changes_buffer, packetLoss);
    enforcer->changes_idx += sizeof(float);

    enforcer->changes_count++;
}


void changeBandwidth(unsigned int src_ip, unsigned int dst_ip, unsigned long bandwidth) {
    printf("[C (manager)] << changeBandwidth %d -> %d ( %ld )\n", src_ip, dst_ip, bandwidth);
    fflush(stdout);

    struct shm_element *enforcer = &enforcer(src_ip % MAX_ENFORCERS);

    putFunction(enforcer->changes_idx, enforcer->changes_buffer, CHANGE_BANDWIDTH);
    enforcer->changes_idx += sizeof(enum function);

//    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, src_ip);
//    enforcer->changes_idx += sizeof(unsigned int);

    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, dst_ip);
    enforcer->changes_idx += sizeof(unsigned int);

    putUInt64(enforcer->changes_idx, enforcer->changes_buffer, bandwidth);
    enforcer->changes_idx += sizeof(unsigned long);

    enforcer->changes_count++;
}

void changeLoss(unsigned int src_ip, unsigned int dst_ip, float packetLoss) {
    printf("[C (manager)] << changeBandwidth %d -> %d ( %f )\n", src_ip, dst_ip, packetLoss);
    fflush(stdout);

    struct shm_element *enforcer = &enforcer(src_ip % MAX_ENFORCERS);

    putFunction(enforcer->changes_idx, enforcer->changes_buffer, CHANGE_LOSS);
    enforcer->changes_idx += sizeof(enum function);

//    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, src_ip);
//    enforcer->changes_idx += sizeof(unsigned int);

    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, dst_ip);
    enforcer->changes_idx += sizeof(unsigned int);

    putFloat(enforcer->changes_idx, enforcer->changes_buffer, packetLoss);
    enforcer->changes_idx += sizeof(float);

    enforcer->changes_count++;
}

void changeLatency(unsigned int src_ip, unsigned int dst_ip, float latency, float jitter) {
    printf("[C (manager)] << changeLatency %d -> %d ( %f, %f )\n", src_ip, dst_ip, latency, jitter);
    fflush(stdout);

    struct shm_element *enforcer = &enforcer(src_ip % MAX_ENFORCERS);

    putFunction(enforcer->changes_idx, enforcer->changes_buffer, CHANGE_LATENCY);
    enforcer->changes_idx += sizeof(enum function);

//    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, src_ip);
//    enforcer->changes_idx += sizeof(unsigned int);

    putUInt32(enforcer->changes_idx, enforcer->changes_buffer, dst_ip);
    enforcer->changes_idx += sizeof(unsigned int);

    putFloat(enforcer->changes_idx, enforcer->changes_buffer, latency);
    enforcer->changes_idx += sizeof(float);

    putFloat(enforcer->changes_idx, enforcer->changes_buffer, jitter);
    enforcer->changes_idx += sizeof(float);

    enforcer->changes_count++;
}



void tearDown() {
    shm_unlink(MASTER_BUFFER_NAME);
    printf("[C (manager)] unlinked buffer.\n");
    fflush(stdout);
}