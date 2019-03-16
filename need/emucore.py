#! /usr/bin/python
from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.XMLGraphParser import XMLGraphParser
from need.NEEDlib.EmulationManager import EmulationManager
from need.NEEDlib.utils import fail, message, ENVIRONMENT, int2ip, ip2int, setup_container

from signal import signal, SIGTERM
import socket
import sys


def get_own_ip(graph):
    # Old way using the netifaces dependency (bad because it has a binary component)
    # interface = os.environ.get(ENVIRONMENT.NETWORK_INTERFACE, 'eth0')
    # if interface is None:
    #     fail("NETWORK_INTERFACE environment variable is not set!")
    # if interface not in netifaces.interfaces():
    #     fail("$NETWORK_INTERFACE: " + interface + " does not exist!")
    # ownIP = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']

    # New way:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_ip = None
    # Connect to at least 2 to avoid using our loopback ip
    for int_ip in graph.hosts_by_ip:
        s.connect((int2ip(int_ip),1))
        new_ip = s.getsockname()[0]
        if new_ip == last_ip:
            break
        last_ip = new_ip
    return last_ip



def main():
    if len(sys.argv) < 4:
        fail("Missing arguments. emucore <topology> <container id>")
    else:
        topology_file = sys.argv[1]
    # For future reference: This topology file must not exceed 512KB otherwise docker refuses
    # to copy it as a config file, this has happened with the 2k scale-free topology...

    setup_container(sys.argv[2], sys.argv[3])

    # Because of the bootstrapper hack we cant get output from the emucore through standard docker logs...
    #sys.stdout = open("/var/log/need.log", "w")
    #sys.stderr = sys.stdout

    graph = NetGraph()

    parser = XMLGraphParser(topology_file, graph)
    parser.fill_graph()
    message("Done parsing topology")

    message("Resolving hostnames...")
    graph.resolve_hostnames()
    message("All hosts found!")

    message("Determining the root of the tree...")
    # Get our own ip address and set the root of the "tree"
    ownIP = get_own_ip(graph)
    graph.root = graph.hosts_by_ip[ip2int(ownIP)]
    if graph.root is None:
        fail("Failed to identify current service instance in topology!")
    message("We are " + graph.root.name + "@" + ownIP)

    message("Calculating shortest paths...")
    graph.calculate_shortest_paths()

    message("Parsing dynamic event schedule...")
    scheduler = parser.parse_schedule(graph.root, graph)

    signal(SIGTERM, lambda signum, frame: exit(0))

    message("Initializing network emulation...")
    manager = EmulationManager(graph, scheduler,ownIP)
    manager.initialize()
    message("Waiting for command to start experiment")
    sys.stdout.flush()
    sys.stderr.flush()

    # Enter the emulation loop
    manager.emulation_loop()

if __name__ == '__main__':
    main()
