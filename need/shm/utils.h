#ifndef UTILS_H
#define UTILS_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "functions.h"


/**********************************************************************************************
*       buffer and different sized ints
**********************************************************************************************/

void putFloat(unsigned int position, unsigned char* buffer, float value) {
    union {
        float f;
        unsigned char b[4];
    } u;

    u.f = value;

    buffer[position]    =  u.b[3];
    buffer[position +1] =  u.b[2];
    buffer[position +2] =  u.b[1];
    buffer[position +3] =  u.b[0];
}

void putUInt64(unsigned int position, unsigned char* buffer, unsigned long value) {
	buffer[position]    =  (value        & 0xFF);
	buffer[position +1] = ((value >>  8) & 0xFF);
	buffer[position +2] = ((value >> 16) & 0xFF);
	buffer[position +3] = ((value >> 24) & 0xFF);
	buffer[position +4] = ((value >> 32) & 0xFF);
	buffer[position +5] = ((value >> 40) & 0xFF);
	buffer[position +6] = ((value >> 48) & 0xFF);
	buffer[position +7] = ((value >> 56) & 0xFF);
}

void putUInt32(unsigned int position, unsigned char* buffer, unsigned int value) {
    buffer[position] = (value & 0xFF);
    buffer[position +1] = ((value >>  8) & 0xFF);
    buffer[position +2] = ((value >> 16) & 0xFF);
    buffer[position +3] = ((value >> 24) & 0xFF);
}

void putUInt16(unsigned int position, unsigned char* buffer, unsigned int value) {
    buffer[position] = ((unsigned short) value & 0xFF);
    buffer[position +1] = (((unsigned short) value >>  8) & 0xFF);
}

void putUInt8(unsigned int position, unsigned char* buffer, unsigned int value) {
    buffer[position] = (unsigned char) value;
}

void putFunction(unsigned int position, unsigned char* buffer, enum function value) {
    buffer[position] = (unsigned char) value;
}


float getFloat(unsigned int position, unsigned char* buffer) {
    union {
        float f;
        unsigned char b[4];
    } u;

    u.b[3] = buffer[position];
    u.b[2] = buffer[position +1];
    u.b[1] = buffer[position +2];
    u.b[0] = buffer[position +3];

    return u.f;
}

unsigned long getUInt64(unsigned int position, unsigned char* buffer) {
    return  (((unsigned long) buffer[position +7]) << 56) |
		    (((unsigned long) buffer[position +6]) << 48) |
			(((unsigned long) buffer[position +5]) << 40) |
			(((unsigned long) buffer[position +4]) << 32) |
			(((unsigned long) buffer[position +3]) << 24) |
			(((unsigned long) buffer[position +2]) << 16) |
			(((unsigned long) buffer[position +1]) <<  8) |
			 ((unsigned long) buffer[position]);
}

unsigned int getUInt32(unsigned int position, unsigned char* buffer) {
    return (((unsigned int) buffer[position +3]) << 24) |
           (((unsigned int) buffer[position +2]) << 16) |
           (((unsigned int) buffer[position +1]) <<  8) |
            ((unsigned int) buffer[position]);
}

unsigned short getUInt16(unsigned int position, unsigned char* buffer) {
    return (((unsigned short) buffer[position +1]) <<  8) |
            ((unsigned short) buffer[position]);
}

char getUInt8(unsigned int position, unsigned char* buffer) {
    return buffer[position];
}

enum function getFunction(unsigned int position, unsigned char* buffer) {
    return (enum function) buffer[position];
}


/**********************************************************************************************
*       IPs
**********************************************************************************************/

//inline std::string intToIP(int intIP) {
//
//    std::vector<unsigned char> b(4);
//    for (int i = 0; i < 4; i++)
//        b[3 - i] = (intIP >> (i * 8));
//
//    int inv = (b[3] << 24) | (b[2] << 16) | (b[1] << 8) | (b[0]);
//
//    struct in_addr ip_addr;
//    ip_addr.s_addr = inv;
//    return inet_ntoa(ip_addr);
//}


/**********************************************************************************************
*       error handling
**********************************************************************************************/

void printBuffer(unsigned char *buffer, unsigned int size) {
    int i = 0;
    printf("[ ");
    for (; i < size; i++)
        printf("%d ", buffer[i]);
    printf("]\n");
}

void printAndFail(char *msg) {
    perror(msg);
    exit(1);
}


#endif