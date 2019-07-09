
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <semaphore.h>
#include <sys/mman.h>
#include <unistd.h>

#include "EnforcerSharedMem.h"

#include "definitions.h"
#include "structures.h"
#include "utils.h"

/******************************************************************************************************/

void (*initDestinationCallback)(unsigned int, unsigned long, float, float, float) = NULL;
void (*changeBandwidthCallback)(unsigned int, unsigned long) = NULL;
void (*changeLossCallback)(unsigned int, float) = NULL;
void (*changeLatencyCallback)(unsigned int, float, float) = NULL;
void (*disconnectCallback) = NULL;
void (*reconnectCallback) = NULL;
void (*tearDownCallback)(int) = NULL;

unsigned int shm_master_fd;         // shared memory file descriptor
struct shm_master  *master;         // pointer to shared memory object
struct shm_semaphores semaphores;   // shared semaphores

unsigned int id;    // identifier for the set of enforcer buffers

/******************************************************************************************************/

void registerInitDestinationCallback(void(*callback)(unsigned int ip, unsigned long bandwidth, float latency, float jitter, float packetLoss)) {
    initDestinationCallback = callback;
}

void registerChangeBandwidthCallback(void(*callback)(unsigned int ip, unsigned long bandwidth)) {
    changeBandwidthCallback = callback;
}

void registerChangeLossCallback(void(*callback)(unsigned int ip, float packetLoss)) {
    changeLossCallback = callback;
}

void registerChangeLatencyCallback(void(*callback)(unsigned int ip, float latency, float jitter)) {
    changeLatencyCallback = callback;
}

void registerDisconnectCallback(void(*callback)()) {
    disconnectCallback = callback;
}

void registerReconnectCallback(void(*callback)()) {
    reconnectCallback = callback;
}

void registerTearDownCallback(void(*callback)(int disableNetwork)) {
    tearDownCallback = callback;
}


/******************************************************************************************************/

void init(unsigned int ip) {
    unsigned int i;
    char str_buffer[64];

	// mutual exclusion semaphore for enforcer buffer acquisition
	while ((semaphores.id_acquisition = sem_open(ID_ACQUISITION_MUTEX_NAME, 0, 0, 0)) == SEM_FAILED) {
		printf("[C (enforcer)] failed sem_open() for id_acquisition_sem; retrying...\n");
		sleep(2);
    }

	// semaphores to control pulling of changes
	while ((semaphores.read_changes = sem_open(READ_CHANGES_MUTEX_NAME, 0, 0, 0)) == SEM_FAILED) {
		printf("[C (enforcer)] failed sem_open() for read_changes_sem; retrying...\n");
		sleep(2);
    }


    // load shared memory structure
    while ((shm_master_fd = shm_open(MASTER_BUFFER_NAME, O_RDWR, 0)) == -1) {
        printf("[C (enforcer)] failed to open shm structure; retrying...\n");
		sleep(2);
    }

    int protections = PROT_READ | PROT_WRITE;
    master = mmap(0, sizeof(struct shm_master), protections, MAP_SHARED, shm_master_fd, 0);
	if (master == MAP_FAILED)
		printAndFail("[C (enforcer)] mapping failed");



//FIXME fix for the new hash map thing
//    // get semaphore and acquire a buffer
//    if (sem_wait(semaphores.id_acquisition) == -1)
//		printAndFail("[C (enforcer)] failed sem_wait() for id_acquisition_sem");
//
//	if ((id = master->enforcer_count) >= MAX_ENFORCERS)
//	    printAndFail("[C (enforcer)] no more available buffers.\n");
//
//    __atomic_add_fetch(&(master->enforcer_count), 1, __ATOMIC_RELAXED);
////	master->enforcer_count++;
//    enforcer(id).ip = ip;
//
//    // release semaphore
//    if (sem_post(semaphores.id_acquisition) == -1)
//		printAndFail("[C (enforcer)] failed sem_post() for id_acquisition_sem");

    id = ip % MAX_ENFORCERS;
    enforcer(id).ip = ip;


    for(i = 0; i < MAX_ENFORCERS; i++) {
    	snprintf(str_buffer, 64, ENFORCER_BUFFER, i);
		if ((semaphores.enforcers[i] = sem_open(str_buffer, 0, 0, 0)) == SEM_FAILED)
		    printAndFail("[C (manager)] failed sem_open() for enforcer_buffer_%d");
    }

    printf("[C (enforcer)] started with id %d.\n", id);
    fflush(stdout);
}


int assertCallbacks() {
    if (initDestinationCallback != NULL && changeBandwidthCallback != NULL && changeLossCallback != NULL
        && changeLatencyCallback != NULL && disconnectCallback != NULL && reconnectCallback != NULL
        && tearDownCallback != NULL) {

        return 0;
    }

    return -1;
}


void addFlow(unsigned int dst_ip, unsigned long bandwidth, unsigned int qlen) {

//    if (sem_wait(semaphores.enforcers[id]) == -1)
//        printAndFail("[C (enforcer)] failed sem_wait() for enforcer_semaphore");

//    printf("[C (enforcer %d)] >> addFlow %d -> %d ( %ld, %d )\n", id, enforcer(id).ip, dst_ip, bandwidth, qlen);
//    fflush(stdout);

    putUInt32(enforcer(id).flows_idx, enforcer(id).flows_buffer, dst_ip);
    enforcer(id).flows_idx += sizeof(unsigned int);

    putUInt64(enforcer(id).flows_idx, enforcer(id).flows_buffer, bandwidth);
    enforcer(id).flows_idx += sizeof(unsigned long);

    putUInt32(enforcer(id).flows_idx, enforcer(id).flows_buffer, qlen);
    enforcer(id).flows_idx += sizeof(unsigned int);

//    enforcer(id).flows_count++;
    __atomic_add_fetch(&(enforcer(id).flows_count), 1, __ATOMIC_RELAXED);

//    if (sem_post(semaphores.enforcers[id]) == -1)
//        printAndFail("[C (enforcer)] failed sem_post() for enforcer_semaphore");
}


void publishFlows() {
//    int aux = enforcer(id).write_buffer;
//    enforcer(id).write_buffer = enforcer(id).read_buffer;
//    enforcer(id).read_buffer = enforcer(id).write_buffer;

//    enforcer(id).active_buffer = (enforcer(id).active_buffer + 1) % MAX_BUFFERS;
//    __atomic_store_n(&(master->writing_in_progress), 1, __ATOMIC_RELAXED);
}


void pullChanges() {
    unsigned int i = 0;
    unsigned int read_idx = 0;

    unsigned int src_ip = enforcer(id).ip, dst_ip;
    unsigned long bandwidth;
    float latency, jitter, packetLoss;

//    if (master->writing_in_progress) {
//        // get semaphore for buffer access
//        if (sem_wait(semaphores.read_changes) == -1)
//            printAndFail("[C (enforcer)] failed sem_wait() for read_changes_sem");
//    }


    for (i = 0; i < enforcer(id).changes_count; i++) {
        switch(getFunction(read_idx, enforcer(id).changes_buffer)) {

            case INIT_DESTINATION :
                read_idx += sizeof(enum function);

//                src_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
//                read_idx += sizeof(unsigned int);

                dst_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(unsigned int);

                bandwidth = getUInt64(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(unsigned long);

                latency = getFloat(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(float);

                jitter = getFloat(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(float);

                packetLoss = getFloat(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(float);

                if (src_ip == enforcer(id).ip) {
                    printf("[C (enforcer)] >> initDestination %d -> %d ( %ld, %f, %f, %f )\n", src_ip, dst_ip, bandwidth, latency, jitter, packetLoss);
                    (*initDestinationCallback)(dst_ip, bandwidth, latency, jitter, packetLoss);
                }

                break;

            case CHANGE_BANDWIDTH :
                read_idx += sizeof(enum function);

//                src_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
//                read_idx += sizeof(unsigned int);

                dst_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(unsigned int);

                bandwidth = getUInt64(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(unsigned long);

                if (src_ip == enforcer(id).ip) {
                    printf("[C (enforcer)] >> changeBandwidth %d -> %d ( %ld )\n", src_ip, dst_ip, bandwidth);
                    (*changeBandwidthCallback)(dst_ip, bandwidth);
                }

                break;

            case CHANGE_LOSS :
                read_idx += sizeof(enum function);

//                src_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
//                read_idx += sizeof(unsigned int);

                dst_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(unsigned int);

                packetLoss = getFloat(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(float);

                if (src_ip == enforcer(id).ip) {
                    printf("[C (enforcer)] >> changeLoss %d -> %d ( %f )\n", src_ip, dst_ip, packetLoss);
                    (*changeLossCallback)(dst_ip, packetLoss);
                }

                break;

            case CHANGE_LATENCY :
                read_idx += sizeof(enum function);

//                src_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
//                read_idx += sizeof(unsigned int);

                dst_ip = getUInt32(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(unsigned int);

                latency = getFloat(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(float);

                jitter = getFloat(read_idx, enforcer(id).changes_buffer);
                read_idx += sizeof(float);

                if (src_ip == enforcer(id).ip) {
                    printf("[C (enforcer)] >> changeLatency %d -> %d ( %f, %f )\n", src_ip, dst_ip, latency, jitter);
                    (*changeLatencyCallback)(dst_ip, latency, jitter);
                }

                break;

            default :
                read_idx += sizeof(enum function);
        }
    }

    fflush(stdout);

    enforcer(id).changes_count = 0;
    enforcer(id).changes_idx = 0;

//    // finished reading, release semaphore
//    if (sem_post(semaphores.read_changes) == -1)
//		printAndFail("[C (enforcer)] failed sem_post() for read_changes_sem");
}



void tearDown() {
    printf("[C (enforcer)] SOMETHING.\n");
    fflush(stdout);
}