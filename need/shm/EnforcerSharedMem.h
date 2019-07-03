#ifndef ENFORCER_SHARED_MEMORY_H
#define ENFORCER_SHARED_MEMORY_H

void registerInitDestinationCallback(void(*callback)(unsigned int ip, unsigned long bandwidth, float latency, float jitter, float packetLoss));
void registerChangeBandwidthCallback(void(*callback)(unsigned int ip, unsigned long bandwidth));
void registerChangeLossCallback(void(*callback)(unsigned int ip, float packetLoss));
void registerChangeLatencyCallback(void(*callback)(unsigned int ip, float latency, float jitter));

void registerDisconnectCallback(void(*callback)());
void registerReconnectCallback(void(*callback)());
void registerTearDownCallback(void(*callback)(int disableNetwork));

void init();
int assertCallbacks();

void addFlow(unsigned int ip, unsigned long bandwidth, unsigned int qlen);
void publishFlows();
void pullChanges();

void tearDown();


#endif
