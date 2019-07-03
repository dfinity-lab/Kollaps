#ifndef FUNCTIONS_H
#define FUNCTIONS_H

enum function {
    INIT_DESTINATION,    // uint_32 IP, uint_32 bandwidth, float latency, float jitter, float packet_loss
    CHANGE_BANDWIDTH,    // uint_32 IP, uint_32 bandwidth
    CHANGE_LOSS,         // uint_32 IP, float packet_loss
    CHANGE_LATENCY,      // uint_32 IP, float latency, float jitter
    DISCONNECT,
    RECONNECT,
    TEARDOWN            // int_32 disableNetwork
};


#endif