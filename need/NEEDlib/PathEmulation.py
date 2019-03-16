from need.NEEDlib.NetGraph import NetGraph
from threading import Lock,RLock
from ctypes import CDLL, c_float, CFUNCTYPE, c_voidp, c_int, c_ulong, c_uint
from os import path
from need.NEEDlib.utils import message
import socket,struct


def long2ip(n):
  return socket.inet_ntoa(struct.pack('!L',n))


def ip2long(ip):
  packedIP = socket.inet_aton(ip)
  return struct.unpack("!L", packedIP)[0]


ownIP = "0.0.0.0"

import sys
if sys.version_info >= (3, 0):
    from typing import Dict, List

class PEState:
    PathLock = Lock()
    shutdown = False
    TCAL = None
    callback = None  # We need to keep a reference otherwise gets garbage collected causing crashes

def init(controll_port,_ip):
    global ownIP
    ownIP = _ip
    with PEState.PathLock:
        if not PEState.shutdown:
            # Get the libTCAL.so full path from the current file
            filepath = path.abspath(__file__)
            folderpath = "/".join(filepath.split('/')[0:-2])
            tcalPath = folderpath + "/TCAL/libTCAL.so"

            PEState.TCAL = CDLL(tcalPath)
            #PEState.TCAL.init(controll_port, 1000)  # 1000 is the txquelen (unit is packets)
            PEState.TCAL.init(controll_port,100)  # 1000 is the txquelen (unit is packets)


def initialize_path(path):
    """
    :param path: NetGraph.Path
    :return:
    """
    if len(path.links) < 1:
        return
    destination = path.links[-1].destination  # type: NetGraph.Service
    bandwidth = path.max_bandwidth
    latency = path.latency
    jitter = path.jitter
    drop = path.drop

    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            message("PE INIT {}".format(destination)) 
            message("PE INIT IP {}".format(destination.ip )) 
            PEState.TCAL.initDestination(destination.ip, int(bandwidth/1000), latency, c_float(jitter), c_float(drop))


def update_usage():
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.updateUsage()


def query_usage(service):
    """
    :param service: NetGraph.Service
    :return: int  # in bytes
    """
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            return PEState.TCAL.queryUsage(service.ip)
        else:
            return 0


def change_bandwidth(service, new_bandwidth):
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in bps
    :return:
    """
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.changeBandwidth(service.ip, int(new_bandwidth/1000))

def change_loss(service, new_loss):
    """
    :param service: NetGraph.Service
    :param new_loss: float
    :return:
    """
    message("PathEmulation change_loss: myself:{} to:{} new_loss: {}".format(ownIP,long2ip(service.ip),new_loss))
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            #message("PE IP: CHANGE_DONE loss {}".format(new_loss))
            PEState.TCAL.changeLoss(ownIP,service.ip, c_float(new_loss))
    message("PathEmulation change_loss: myself:{} to:{} new_loss: {} DONE".format(ownIP,long2ip(service.ip),new_loss))

def change_loss_by_ip(ip, new_loss):
    """
    :param service: NetGraph.Service
    :param new_loss: float
    :return:
    """
    message("PathEmulation change_loss_by_ip: myself:{} to:{} new_loss: {}".format(ownIP,long2ip(ip),new_loss))
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.changeLoss(ownIP,ip, c_float(new_loss))
    message("PathEmulation change_loss_by_ip: myself:{} to:{} new_loss: {} DONE".format(ownIP,long2ip(ip),new_loss))


def change_latency_by_ip(ip, latency, jitter):
    """
    :param service:
    :param latency:
    :param jitter:
    :return:
    """
    message("PathEmulation change_latency_by_ip: from:{} to:{} new_loss: {}".format(ownIP,long2ip(ip),latency))
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.changeLatency(ip, latency, c_float(jitter))

    message("PathEmulation change_latency_by_ip: from:{} to:{} new_loss: {} DONE".format(ownIP,long2ip(ip),latency))


def change_latency(service, latency, jitter):
    """
    :param service:
    :param latency:
    :param jitter:
    :return:
    """
    pass
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.changeLatency(service.ip, latency, c_float(jitter))


def register_usage_callback(callback):
    """
    :param callback: func
    :return:
    """
    CALLBACKTYPE = CFUNCTYPE(c_voidp, c_uint, c_ulong, c_uint)
    c_callback = CALLBACKTYPE(callback)
    PEState.callback = c_callback
    with PEState.PathLock:
        if not PEState.shutdown and PEState.TCAL:
            PEState.TCAL.registerUsageCallback(c_callback)


def disconnect():
    with PEState.PathLock:
        PEState.TCAL.disconnect()

def reconnect():
    with PEState.PathLock:
        PEState.TCAL.reconnect()

def tearDown():
    with PEState.PathLock:
        PEState.shutdown = True
        if PEState.TCAL:
            PEState.TCAL.tearDown(0)
