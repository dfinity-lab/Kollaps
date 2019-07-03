#ifndef MANAGER_SHARED_MEMORY_H
#define MANAGER_SHARED_MEMORY_H

void registerFlowCollectorCallback(void(*callback)(unsigned int src_ip, unsigned int dst_ip, unsigned long bandwidth, unsigned int qlen));

void init(unsigned int numberOfEnforcers);

void pullFlows();
void lock_changes();
void publishChanges();

void initDestination(unsigned int src_ip, unsigned int dst_ip, unsigned long bandwidth, float latency, float jitter, float packetLoss);
void changeBandwidth(unsigned int src_ip, unsigned int dst_ip, unsigned long bandwidth);
void changeLoss(unsigned int src_ip, unsigned int dst_ip, float packetLoss);
void changeLatency(unsigned int src_ip, unsigned int dst_ip, float latency, float jitter);

unsigned long queryUsage(unsigned int src_ip, unsigned int dst_ip);

void tearDown();


#endif
