#ifndef STRUCRURES_H
#define STRUCRURES_H

#include <semaphore.h>

#include "definitions.h"

// struct holding an individual shared buffer
struct shm_element {
	unsigned int ip;

	unsigned int flows_count;
	unsigned int flows_idx;
	unsigned char flows_buffer[BUFFER_LENGTH];

	unsigned int changes_count;
	unsigned int changes_idx;
	unsigned char changes_buffer[BUFFER_LENGTH];
};

// struct holding the set of shared buffers
struct shm_master {
	struct shm_element manager_elem;
	struct shm_element enforcers[MAX_ENFORCERS];
	unsigned int enforcer_count;
	int writing_in_progress;
};

// struct holding all the semaphores to be used during the emulation
struct shm_semaphores {
	sem_t* id_acquisition;
	sem_t* read_changes;
	sem_t* write_changes;
	sem_t* enforcers[MAX_ENFORCERS];
};


#endif