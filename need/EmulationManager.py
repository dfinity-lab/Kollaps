#! /usr/bin/python

import sys
import socket
import docker

from os import path, getenv
from signal import signal, SIGTERM
from time import sleep
from ctypes import CDLL

from pprint import pprint
from signal import signal, SIGTERM

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser
from need.NEEDlib.EmulationCore import EmulationCore
from need.NEEDlib.utils import int2ip, ip2int, DOCKER_SOCK
from need.NEEDlib.utils import print_and_fail, print_named


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
    return folder_path + "/shm/ManagerSharedMem.so"


def map_names_ips():
    low_level_client = docker.APIClient(base_url='unix:/' + DOCKER_SOCK)
    overlay_config = low_level_client.inspect_network(getenv('OVERLAY_NAME', ''))

    names_and_ips = {}
    for container in overlay_config['Containers'].values():
        names_and_ips[container['Name'].rsplit('.', 1)[0]] = container['IPv4Address'].rsplit('/', 1)[0]

    return names_and_ips


def main():
    if len(sys.argv) < 4:
        print_and_fail("Missing arguments. emucore <topology> <container id>")

    # For future reference: This topology file must not exceed 512KB otherwise docker refuses
    # to copy it as a config file, this has happened with the 2k scale-free topology...
    topology_file = sys.argv[1]

    # Because of the bootstrapper hack we cant get output from the emucore through standard docker logs...
    # sys.stdout = open("/var/log/need.log", "w")
    # sys.stderr = sys.stdout

    graph = NetGraph()

    # parse the topology
    parser = XMLGraphParser(topology_file, graph)
    parser.fill_graph()


    # FIXME make sure all hosts exist, get our own IP and set the root of the "tree"

    graph.assign_ips(map_names_ips())

    str_to_print = ""
    for ip_as_int, host in graph.hosts_by_ip.items():
        str_to_print += "\n    " + str(int2ip(ip_as_int)) + "\t" + str(host.name) + "\t" + str(host.ip)
    print_named("after IP mapping", str_to_print)

    graph.calculate_shortest_paths()

    print_named("FAIL", f":: {len(graph.paths_by_id)} ::")

    # FIXME
    # graph.resolve_hostnames()
    # own_ip = get_own_ip(graph)
    # graph.root = graph.hosts_by_ip[ip2int(own_ip)]

    # if graph.root is None:
    #     print_and_fail("Failed to identify current service instance in topology!")

    # graph.calculate_shortest_paths()

    # parse schedule for the dynamic events
    # FIXME
    # scheduler = parser.parse_schedule(graph.root, graph)
    scheduler = None

    signal(SIGTERM, lambda signum, frame: exit(0))

    print_named("EmuManager", "setup finished, initializing network emulation...")

    # initialization of the emulation manager
    manager_lib = CDLL(get_shared_lib_path())
    manager_lib.init(len(graph.services))

    emucore = EmulationCore(manager_lib, graph, scheduler)
    emucore.initialize()
    sleep(5)
    
    print_named("EmuManager", "waiting for command to start experiment...")
    sys.stdout.flush()
    sys.stderr.flush()

    # enter the emulation loop
    emucore.emulation_loop()


if __name__ == '__main__':
    main()