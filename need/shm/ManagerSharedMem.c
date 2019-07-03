
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
	manager.count = 0;
	manager.buffer_idx = 0;
	for(i = 0; i < MAX_BUFFERS; i++) {
    	snprintf(str_buffer, 64, ENFORCER_BUFFER, i);
		if ((semaphores.enforcers[i] = sem_open(str_buffer, O_CREAT, 0660, 0)) == SEM_FAILED)
		    printAndFail("[C (manager)] failed sem_open() for enforcer_buffer_%d");

        sem_post(semaphores.enforcers[i]);

	    enforcer(i).count = 0;
	    enforcer(i).buffer_idx = 0;
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

    for (i = 0; i < master->enforcer_count; i++) {

        if (sem_wait(semaphores.enforcers[i]) == -1)
		    printAndFail("[C (manager)] failed sem_wait() for enforcer_semaphore");

        read_idx = 0;
        for (j = 0; j < enforcer(i).count; j++) {
            dst_ip = getUInt32(read_idx, enforcer(i).buffer);
            read_idx += sizeof(unsigned int);

            bandwidth = getUInt64(read_idx, enforcer(i).buffer);
            read_idx += sizeof(unsigned long);

            qlen = getUInt32(read_idx, enforcer(i).buffer);
            read_idx += sizeof(unsigned int);

            printf("[C (manager)] << newFlow( %d, %d, %ld, %d ) from %d\n", enforcer(i).ip, dst_ip, bandwidth, qlen, i);
            (*flowCollectorCallback)(enforcer(i).ip, dst_ip, bandwidth, qlen);
        }

        enforcer(i).count = 0;
        enforcer(i).buffer_idx = 0;
//        __atomic_store_n(&(enforcer(i).count), 0, __ATOMIC_RELAXED);
//        __atomic_store_n(&(enforcer(i).buffer_idx), 0, __ATOMIC_RELAXED);

        fflush(stdout);

        if (sem_post(semaphores.enforcers[i]) == -1)
		    printAndFail("[C (manager)] failed sem_post() for enforcer_semaphore");
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

    manager.count = 0;
    manager.buffer_idx = 0;

//    printf("[C (manager)] locked changes buffer.\n");
//    fflush(stdout);
}

void publishChanges() {
    __atomic_store_n(&(master->writing_in_progress), 0, __ATOMIC_RELAXED);

    int i = 0;
    for (i = 0; i <= master->enforcer_count; i++)
        if (sem_post(semaphores.read_changes) == -1)
            printAndFail("[C (manager)] failed sem_post() for read_changes_sem");

    if (manager.count > 0) {
        printf("[C (manager)] published changes and freed buffer.\n");
        fflush(stdout);
    }

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
    printf("[C (manager)] << initDestination( %d, %d, %ld, %f, %f, %f )\n", src_ip, dst_ip, bandwidth, latency, jitter, packetLoss);
    fflush(stdout);

    putFunction(manager.buffer_idx, manager.buffer, INIT_DESTINATION);
    manager.buffer_idx += sizeof(enum function);
    
    putUInt32(manager.buffer_idx, manager.buffer, src_ip);
    manager.buffer_idx += sizeof(unsigned int);

    putUInt32(manager.buffer_idx, manager.buffer, dst_ip);
    manager.buffer_idx += sizeof(unsigned int);
    
    putUInt64(manager.buffer_idx, manager.buffer, bandwidth);
    manager.buffer_idx += sizeof(unsigned long);
    
    putFloat(manager.buffer_idx, manager.buffer, latency);
    manager.buffer_idx += sizeof(float);
    
    putFloat(manager.buffer_idx, manager.buffer, jitter);
    manager.buffer_idx += sizeof(float);
    
    putFloat(manager.buffer_idx, manager.buffer, packetLoss);
    manager.buffer_idx += sizeof(float);

    manager.count++;
}


void changeBandwidth(unsigned int src_ip, unsigned int dst_ip, unsigned long bandwidth) {
    printf("[C (manager)] << changeBandwidth( %d, %d, %ld )\n", src_ip, dst_ip, bandwidth);
    fflush(stdout);

    putFunction(manager.buffer_idx, manager.buffer, CHANGE_BANDWIDTH);
    manager.buffer_idx += sizeof(enum function);

    putUInt32(manager.buffer_idx, manager.buffer, src_ip);
    manager.buffer_idx += sizeof(unsigned int);

    putUInt32(manager.buffer_idx, manager.buffer, dst_ip);
    manager.buffer_idx += sizeof(unsigned int);

    putUInt64(manager.buffer_idx, manager.buffer, bandwidth);
    manager.buffer_idx += sizeof(unsigned long);

    manager.count++;
}

void changeLoss(unsigned int src_ip, unsigned int dst_ip, float packetLoss) {
    printf("[C (manager)] << changeBandwidth( %d, %d, %f )\n", src_ip, dst_ip, packetLoss);
    fflush(stdout);

    putFunction(manager.buffer_idx, manager.buffer, CHANGE_LOSS);
    manager.buffer_idx += sizeof(enum function);

    putUInt32(manager.buffer_idx, manager.buffer, src_ip);
    manager.buffer_idx += sizeof(unsigned int);

    putUInt32(manager.buffer_idx, manager.buffer, dst_ip);
    manager.buffer_idx += sizeof(unsigned int);

    putFloat(manager.buffer_idx, manager.buffer, packetLoss);
    manager.buffer_idx += sizeof(float);

    manager.count++;
}

void changeLatency(unsigned int src_ip, unsigned int dst_ip, float latency, float jitter) {
    printf("[C (manager)] << changeLatency( %d, %d, %f, %f )\n", src_ip, dst_ip, latency, jitter);
    fflush(stdout);

    putFunction(manager.buffer_idx, manager.buffer, CHANGE_LATENCY);
    manager.buffer_idx += sizeof(enum function);

    putUInt32(manager.buffer_idx, manager.buffer, src_ip);
    manager.buffer_idx += sizeof(unsigned int);

    putUInt32(manager.buffer_idx, manager.buffer, dst_ip);
    manager.buffer_idx += sizeof(unsigned int);

    putFloat(manager.buffer_idx, manager.buffer, latency);
    manager.buffer_idx += sizeof(float);

    putFloat(manager.buffer_idx, manager.buffer, jitter);
    manager.buffer_idx += sizeof(float);

    manager.count++;
}



void tearDown() {
    shm_unlink(MASTER_BUFFER_NAME);
    printf("[C (manager)] unlinked buffer.\n");
    fflush(stdout);
}