
import struct
import ctypes

from ctypes import CFUNCTYPE, POINTER, c_voidp, c_uint, c_ulong, c_bool
from threading import Lock

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.EventScheduler import EventScheduler
from need.NEEDlib.utils import BYTE_LIMIT, SHORT_LIMIT
from need.NEEDlib.utils import LOCAL_IPS_FILE, REMOTE_IPS_FILE, AERON_LIB_PATH
from need.NEEDlib.utils import int2ip, ip2int
from need.NEEDlib.utils import print_identified, print_and_fail, print_error_named


class AeronHandler:
	UDP_PORT = 7073
	MIN_MTU = 576
	MAX_IP_HDR = 60
	UDP_HDR = 8
	BUFFER_LEN = MIN_MTU - MAX_IP_HDR - UDP_HDR
	STOP_COMMAND = 1
	SHUTDOWN_COMMAND = 2
	READY_COMMAND = 3
	START_COMMAND = 4
	ACK = 120
	i_SIZE = struct.calcsize("<1i")
	MAX_WORKERS = 1
	
	
	def __init__(self, flow_collector, graph, event_scheduler, ip=None):
		self.graph = graph  # type: NetGraph
		self.scheduler = event_scheduler  # type: EventScheduler
		self.flow_collector = flow_collector
		self.produced = 0
		self.received = 0
		self.consumed = 0
		self.largest_produced_gap = -1
		self.stop_lock = Lock()
		
		self.aeron_lib = None
		self.aeron_id = None
		self.local_ips = {}
		self.remote_ips = {}
		
		link_count = len(self.graph.links)
		if link_count <= BYTE_LIMIT:
			self.link_unit = "1B"
		elif link_count <= SHORT_LIMIT:
			self.link_unit = "1H"
		else:
			print_and_fail("Topology has too many links: " + str(link_count))
		self.link_size = struct.calcsize("<" + self.link_unit)
		
		self.supervisor_count = 0
		self.peer_count = 0
		
		
		# FIXME
		# if ip is None:
		# 	self.aeron_id = self.graph.root.ip
		# else:
		# 	self.aeron_id = ip2int(ip)
		self.aeron_id = 167772161
		
			
		for service in self.graph.services:
			hosts = self.graph.services[service]
			for host in hosts:
				# if host != self.graph.root:	# count self, will be subtracted later
				# 	self.peer_count += 1
				
				if host.supervisor:
					self.supervisor_count += 1
					
		self.peer_count -= self.supervisor_count + 1	# subtract self counted on the loop above
		
		# setup python callback
		self.aeron_lib = ctypes.CDLL(AERON_LIB_PATH)
		
		if link_count <= BYTE_LIMIT:
			self.aeron_lib.init(self.aeron_id, False)
			self.flow_adding_func = self.aeron_lib.addFlow8
		
		else:
			self.aeron_lib.init(self.aeron_id, True)
			self.flow_adding_func = self.aeron_lib.addFlow16
		
		CALLBACKTYPE = CFUNCTYPE(c_voidp, c_ulong, c_uint, POINTER(c_uint))
		c_callback = CALLBACKTYPE(self.receive_flow)
		self.callback = c_callback  # keep reference so it does not get garbage collected
		self.aeron_lib.registerCallback(self.callback)
		
		# TODO PG run through this again, rename variables to match new god logs functionality
		my_starting_links = []
		for key, path in self.graph.paths_by_id.items():
			if len(path.links) > 0 and path.links[0].index not in my_starting_links:
				my_starting_links.append(path.links[0].index)
		
		with open(LOCAL_IPS_FILE, 'r') as file:
			for line in file.readlines():
				self.aeron_lib.addLocalSubs(int(line), len(my_starting_links),
											(c_uint * len(my_starting_links))(*my_starting_links))
		
		with open(REMOTE_IPS_FILE, 'r') as file:
			for line in file.readlines():
				self.aeron_lib.addRemoteSubs(int(line))
		
		self.aeron_lib.startPolling()
	
	
	def add_flow(self, throughput, link_list):
		self.flow_adding_func(throughput, len(link_list), (c_uint * len(link_list))(*link_list))
	
	
	def receive_flow(self, bandwidth, link_count, link_list):
		# print_named("(received)", "throughput: " + str(bandwidth) + " links: " + str(link_list[:link_count]))
		self.flow_collector(bandwidth, link_list[:link_count])
		self.received += 1
	
	
	def clear_flows_to_be_sent(self):
		self.aeron_lib.clearFlows()
	
	
	def broadcast_flows(self, active_paths):
		"""
		:param active_paths: List[NetGraph.Path]
		:return:
		"""
		try:
			with self.stop_lock:
				if len(active_paths) > 0:
					self.produced += self.peer_count
					
					for path in active_paths:
						links = [link.index for link in path.links]
						self.flow_adding_func(int(path.used_bandwidth), len(links), (c_uint * len(links))(*links))
					
					self.aeron_lib.flush()
		
		except Exception as e:
			print_error_named("broadcast_flows", str(e))
	
	
	def shutdown(self):
		self.aeron_lib.teardown()
	
	