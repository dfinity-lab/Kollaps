#! /usr/bin/python

import sys
import socket

from os import path, getenv
from signal import signal, SIGTERM
from time import time, sleep
from ctypes import CDLL, CFUNCTYPE, POINTER, c_voidp, c_uint, c_ulong, c_float


import need.NEEDlib.communications.TCALHandler as TCALHandler
from need.NEEDlib.communications.DashboardHandler import DashboardHandler

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser
from need.NEEDlib.utils import int2ip, ip2int, setup_container
from need.NEEDlib.utils import print_and_fail, print_identified, print_named


UDP_PORT = 7073


def get_own_ip(graph):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_ip = None

    # Connect to at least 2 to avoid using our loopback ip
    for int_ip in graph.hosts_by_ip:
        s.connect((int2ip(int_ip), 1))
        new_ip = s.getsockname()[0]
        if new_ip == last_ip:
            break
        last_ip = new_ip

    return last_ip


def get_shared_lib_path():
    file_path = path.abspath(__file__)
    folder_path = "/".join(file_path.split('/')[0:-1])
    return folder_path + "/shm/EnforcerSharedMem.so"


def setup_callbacks(enforcer_lib):
    callbacks = []

    callback_type = CFUNCTYPE(c_voidp, c_uint, c_ulong, c_float, c_float, c_float)
    callback = callback_type(TCALHandler.initialize_destination)
    callbacks.append(callback)
    enforcer_lib.registerInitDestinationCallback(callback)

    callback_type = CFUNCTYPE(c_voidp, c_uint, c_ulong)
    callback = callback_type(TCALHandler.change_bandwidth)
    callbacks.append(callback)
    enforcer_lib.registerChangeBandwidthCallback(callback)

    callback_type = CFUNCTYPE(c_voidp, c_uint, c_float)
    callback = callback_type(TCALHandler.change_loss)
    callbacks.append(callback)
    enforcer_lib.registerChangeLossCallback(callback)

    callback_type = CFUNCTYPE(c_voidp, c_uint, c_float, c_float)
    callback = callback_type(TCALHandler.change_latency)
    callbacks.append(callback)
    enforcer_lib.registerChangeLatencyCallback(callback)

    callback_type = CFUNCTYPE(c_voidp)
    callback = callback_type(TCALHandler.disconnect)
    callbacks.append(callback)
    enforcer_lib.registerDisconnectCallback(callback)

    callback_type = CFUNCTYPE(c_voidp)
    callback = callback_type(TCALHandler.reconnect)
    callbacks.append(callback)
    enforcer_lib.registerReconnectCallback(callback)

    callback_type = CFUNCTYPE(c_voidp)
    callback = callback_type(TCALHandler.teardown)
    callbacks.append(callback)
    enforcer_lib.registerTearDownCallback(callback)

    if enforcer_lib.assertCallbacks() != 0:
        print_and_fail("failed to setup callbacks on the Emulation Enforcer.")

    return callbacks


def main():
    if len(sys.argv) < 4:
        print_and_fail("Missing arguments. \nEmulationEnforcer <topology> <container id>")

    # For future reference: This topology file must not exceed 512KB otherwise docker refuses
    # to copy it as a config file, this has happened with the 2k scale-free topology...
    topology_file = sys.argv[1]

    setup_container(sys.argv[2], sys.argv[3])

    # Because of the bootstrapper hack we cant get output from the emucore through standard docker logs...
    # sys.stdout = open("/var/log/need.log", "w")
    # sys.stderr = sys.stdout
    
    graph = NetGraph()
    
    # parse the topology
    parser = XMLGraphParser(topology_file, graph)
    parser.fill_graph()
    
    # make sure all hosts exist, get our own IP and set the root of the "tree"
    graph.resolve_hostnames()
    own_ip = get_own_ip(graph)
    graph.root = graph.hosts_by_ip[ip2int(own_ip)]
    
    if graph.root is None:
        print_and_fail("Failed to identify current service instance in topology!")

    graph.calculate_shortest_paths()

    # parse schedule for the dynamic events
    scheduler = parser.parse_schedule(graph.root, graph)

    signal(SIGTERM, lambda signum, frame: exit(0))

    print_identified(graph, "setup finished, initializing network emulation...")

    # setup communication with the dashboard
    dashboard = DashboardHandler(scheduler)

    # setup the c shared memory library
    enforcer_lib = CDLL(get_shared_lib_path())
    enforcer_lib.init(ip2int(own_ip))
    
    # setup the tc abstraction layer
    TCALHandler.init(UDP_PORT)
    TCALHandler.register_usage_callback(enforcer_lib.addFlow)
    
    # keep references to callbacks to avoid garbage collection
    callbacks = setup_callbacks(enforcer_lib)

    print_identified(graph, "waiting for command to start experiment...")
    sys.stdout.flush()
    sys.stderr.flush()

    # enter the emulation loop
    POOL_PERIOD = float(getenv('POOL_PERIOD', 0.05))  # in seconds
    last_time = time()

    while True:
        sleep_time = POOL_PERIOD - (time() - last_time)

        if sleep_time > 0.0:
            sleep(sleep_time)

        last_time = time()

        enforcer_lib.pullChanges()
        TCALHandler.update_usage()


if __name__ == '__main__':
    main()
