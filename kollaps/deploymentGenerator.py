#! /usr/bin/python

import sys
import os

from kollaps.Kollapslib.NetGraph import NetGraph
from kollaps.Kollapslib.XMLGraphParser import XMLGraphParser
from kollaps.Kollapslib.deploymentGenerators.DockerComposeFileGenerator import DockerComposeFileGenerator
from kollaps.Kollapslib.deploymentGenerators.KubernetesManifestGenerator import KubernetesManifestGenerator
from kollaps.Kollapslib.utils import SHORT_LIMIT
from kollaps.Kollapslib.utils import print_message, print_error, print_and_fail


def main():
    if len(sys.argv) != 3:
        msg = "Usage: deploymentGenerator.py <input topology> <orchestrator> > <output compose file>\n" \
             + "    <orchestrator> can be -s for Docker Swarm or -k for Kubernetes"
        
        print_and_fail(msg)
        
    
    shm_size = 8000000000
    aeron_lib_path = "/home/daedalus/Documents/aeron4need/cppbuild/Release/lib/libaeronlib.so"
    aeron_term_buffer_length = 2*64*1024*1024           # must be multiple of 64*1024
    aeron_ipc_term_buffer_length = 2*64*1024*1024   	# must be multiple of 64*1024

    threading_mode = 'SHARED'             # aeron uses 1 thread
    # threading_mode = 'SHARED_NETWORK'   # aeron uses 2 threads
    # threading_mode = 'DEDICATED'        # aeron uses 3 threads

    pool_period = 0.05
    max_flow_age = 2
    
    output = ""
    
    topology_file = sys.argv[1]
    # TODO use argparse to support other orchestrators
    orchestrator = "kubernetes" if sys.argv[2] == "-k" else "swarm"
    graph = NetGraph()

    XMLGraphParser(topology_file, graph).fill_graph()
    output += "Graph has " + str(len(graph.links)) + " links.\n"
    service_count = 0
    
    for hosts in graph.services:
        for host in graph.services[hosts]:
            service_count += 1
            
    output += "      has " + str(service_count) + " hosts.\n"

    if len(graph.links) > SHORT_LIMIT:
        print_and_fail("Topology has too many links: " + str(len(graph.links)))
        
    for path in graph.paths:
        if len(path.links) > 249:
            msg = "Path from " + path.links[0].source.name + " to " \
                  + path.links[-1].destination.name + " is too long (over 249 hops)"
            print_and_fail(msg)
    
    generator = None
    if orchestrator == "kubernetes":
        generator = KubernetesManifestGenerator(os.getcwd() + "/" + topology_file, graph)

    elif orchestrator == 'swarm':
        generator = DockerComposeFileGenerator(topology_file, graph)
        
    # insert here any other generators required by new orchestrators
    else:
        pass
    
    if generator is not None:
        generator.generate(pool_period, max_flow_age, threading_mode, shm_size, aeron_lib_path, aeron_term_buffer_length, aeron_ipc_term_buffer_length)
        output += "Experiment UUID: " + generator.experiment_UUID
        print(output, file=sys.stderr)
        
    else:
        print("Failed to find a suitable generator.", file=sys.stderr)


if __name__ == '__main__':
    main()
    
    