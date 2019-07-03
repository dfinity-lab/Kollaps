
from os import path
from threading import Lock
from ctypes import CDLL, c_float, CFUNCTYPE, c_voidp, c_int, c_ulong, c_uint

from need.NEEDlib.NetGraph import NetGraph


class HandlerState:
    PathLock = Lock()
    shutdown = False
    TCAL = None
    callback = None  # We need to keep a reference otherwise gets garbage collected causing crashes


def init(controll_port):
    with HandlerState.PathLock:
        if not HandlerState.shutdown:
            # Get the libTCAL.so full path from the current file
            file_path = path.abspath(__file__)
            folder_path = "/".join(file_path.split('/')[0:-3])
            tcal_path = folder_path + "/TCAL/libTCAL.so"
            
            HandlerState.TCAL = CDLL(tcal_path)
            HandlerState.TCAL.init(controll_port, 1000)  # 1000 is the txquelen (unit is packets)


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

    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.initDestination(destination.ip, int(bandwidth/1000), c_float(latency), c_float(jitter), c_float(drop))


def initialize_destination(ip, bandwidth, latency, jitter, drop):
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.initDestination(ip, int(bandwidth/1000), c_float(latency), c_float(jitter), c_float(drop))


def disable_path(service):
    """
    :param service: NetGraph.Service
    :return:
    We choose 10kbit rather randomly here. The problem is that bandwidth will only be changed for active paths,
    and if we take a super small value here, a path will never be active (in the emulation manager). Hence after
    activating the path disabled here (ie. by adding new links), nothing will flow through them. LL based on comments by JN
    """
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.initDestination(service.ip, 10000, c_float(1), c_float(0), c_float(1))


def update_usage():
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.updateUsage()


def query_usage(service):
    """
    :param service: NetGraph.Service
    :return: int  # in bytes
    """
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            return HandlerState.TCAL.queryUsage(service.ip)
        else:
            return 0


def change_bandwidth(service, new_bandwidth):
    """
    :param service: NetGraph.Service
    :param new_bandwidth: int  # in bps
    :return:
    """
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.changeBandwidth(service.ip, int(new_bandwidth/1000))


def change_loss(service, new_loss):
    """
    :param service: NetGraph.Service
    :param new_loss: float
    :return:
    """
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.changeLoss(service.ip, c_float(new_loss))


def change_latency(service, latency, jitter):
    """
    :param service:
    :param latency:
    :param jitter:
    :return:
    """
    pass
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.changeLatency(service.ip, c_float(latency), c_float(jitter))


def register_usage_callback(callback):
    """
    :param callback: func
    :return:
    """
    CALLBACKTYPE = CFUNCTYPE(c_voidp, c_uint, c_ulong, c_uint)
    c_callback = CALLBACKTYPE(callback)
    HandlerState.callback = c_callback
    with HandlerState.PathLock:
        if not HandlerState.shutdown and HandlerState.TCAL:
            HandlerState.TCAL.registerUsageCallback(c_callback)


def disconnect():
    with HandlerState.PathLock:
        HandlerState.TCAL.disconnect()


def reconnect():
    with HandlerState.PathLock:
        HandlerState.TCAL.reconnect()


def teardown():
    with HandlerState.PathLock:
        HandlerState.shutdown = True
        if HandlerState.TCAL:
            HandlerState.TCAL.tearDown(0)

