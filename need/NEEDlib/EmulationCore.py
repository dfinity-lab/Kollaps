
import socket

from time import time, sleep
from threading import Lock
from os import environ, getenv
from typing import Dict, List
from ctypes import CDLL, c_float, CFUNCTYPE, c_voidp, c_int, c_ulong, c_uint

from need.NEEDlib.NetGraph import NetGraph
from need.NEEDlib.EventScheduler import EventScheduler
from need.NEEDlib.communications.AeronHandler import AeronHandler
from need.NEEDlib.utils import ENVIRONMENT
from need.NEEDlib.utils import print_named, print_message, print_identified


# Global variable used within the callback to TCAL
emuManager = None  # type: EmulationCore


def collect_usage(src_ip, dst_ip, sent_bytes, qlen):  # qlen: number of packets in the qdisc, max is txqueuelen
	emuManager.collect_own_flow(src_ip, dst_ip, sent_bytes, qlen)


class EmulationCore:
	
	# Generic loop tuning
	ERROR_MARGIN = 0.01	# in percent
	POOL_PERIOD = float(getenv('POOL_PERIOD', 0.05))		# in seconds
	ITERATIONS_TO_INTEGRATE = int(getenv('ITERATIONS', 1))	# how many times POOL_PERIOD
	MAX_FLOW_AGE = int(getenv('MAX_FLOW_AGE', 2))			# times a flow is kept before deletion

	# Exponential weighted moving average tuning
	ALPHA = 0.25
	ONE_MINUS_ALPHA = 1-ALPHA
	
	
	def __init__(self, manager_lib, net_graph, event_scheduler):
		self.manager_lib = manager_lib
		self.graph = net_graph				# type: NetGraph
		self.scheduler = event_scheduler	# type: EventScheduler
		self.active_paths = []				# type: List[NetGraph.Path]
		self.active_paths_ids = []			# type: List[int]
		self.flow_accumulator = {}			# type: Dict[str, List[List[int], int, int]]
		self.flow_accumulator_callback = None
		self.state_lock = Lock()
		self.last_time = 0
		# self.delayed_flows = 0
		
		EmulationCore.POOL_PERIOD = float(environ.get(ENVIRONMENT.POOL_PERIOD, str(EmulationCore.POOL_PERIOD)))
		EmulationCore.ITERATIONS_TO_INTEGRATE = int(environ.get(ENVIRONMENT.ITERATION_COUNT,
																   str(EmulationCore.ITERATIONS_TO_INTEGRATE)))
		
		print_message("Pool Period: " + str(EmulationCore.POOL_PERIOD))
		# print_message("Iteration Count: " + str(EmulationCore.ITERATIONS_TO_INTEGRATE))
		
		self.check_flows_time_delta = 0
		# We need to give the callback a reference to ourselves (kind of hackish...)
		global emuManager
		emuManager = self

		own_ip = socket.gethostbyname(socket.gethostname())

		self.comms = AeronHandler(self.collect_flow, self.graph, self.scheduler, own_ip)


	def initialize(self):
		for path_id, path in self.graph.paths_by_id.items():
			
			if len(path.links) > 0:
				src_service = path.links[0].source
				dst_service = path.links[-1].destination
				
				if isinstance(src_service, NetGraph.Service) and isinstance(dst_service, NetGraph.Service):
					src_ip = src_service.ip
					dst_ip = dst_service.ip
					bandwidth = path.max_bandwidth
					latency = path.latency
					jitter = path.jitter
					drop = path.drop
					
					self.manager_lib.initDestination(src_ip, dst_ip, int(bandwidth / 1000), c_float(latency), c_float(jitter), c_float(drop))
		
		
		# LL: also drop everything that goes towards a host we don't see
		for service in self.graph.services.values():
			for service_instance in service:
				if service_instance not in self.graph.paths and not service_instance.supervisor:
					self.manager_lib.initDestination(service_instance.ip, 10000, c_float(1), c_float(0), c_float(1))
		
		
		CALLBACKTYPE = CFUNCTYPE(c_voidp, c_uint, c_uint, c_ulong, c_uint)
		c_callback = CALLBACKTYPE(collect_usage)
		self.flow_accumulator_callback = c_callback
		self.manager_lib.registerFlowCollectorCallback(c_callback)
		
		self.manager_lib.publishChanges()
		

	# What check_active_flows does is call PathEmulation.update_usage(), which calls TCAL.update_usage(), which calls TC_updateUsage().
	# This function requests a dump of the statistics kept by tc, which is done by calling update_class() once for each tc class.
	# Since there is a 1:1 relationship between HTC classes to hosts, this is performed once for each host.
	# If there was a flow (>0B sent), it calls the registered usageCallback(), which is this class' collect_usage() method.
	# Therefore, check_active_flows() basically calls collect_own_flow() once for each host.
	# LL based on information from JN
	def emulation_loop(self):
		self.last_time = time()
		self.check_active_flows()  # to prevent bug where data has already passed through the filters before
		last_time = time()
		
		try:
			while True:
				
				# for i in range(EmulationCore.ITERATIONS_TO_INTEGRATE):		# CHANGED iteration count
				sleep_time = EmulationCore.POOL_PERIOD - (time() - last_time)
				
				if sleep_time > 0.0:
					sleep(sleep_time)
					
				last_time = time()
				
				with self.state_lock:
					self.active_paths.clear()
					self.active_paths_ids.clear()
					self.check_active_flows()
						
				# aeron is reliable so send only once
				self.comms.broadcast_flows(self.active_paths)
				
				with self.state_lock:
					# self.manager_lib.lock_changes()
					self.apply_bandwidth()
					# self.manager_lib.publishChanges()
			
			# self.flow_accumulator.clear()		# CHANGED dont clear here
				
		# except KeyboardInterrupt:
		# 	print_identified(self.graph, "closed with KeyboardInterrupt")
		
		except:
			# print_identified(self.graph, f"used {self.delayed_flows} cached flows")
			pass
		
	
	def apply_flow(self, flow):
		link_indices = flow[0]	# flow.INDICES
		bandwidth = flow[1]		# flow.BW

		# Calculate RTT of this flow
		rtt = 0
		for index in link_indices:
			link = self.graph.links_by_index[index]
			with link.lock:
				rtt += (link.latency * 2)

		# Add it to the link's flows
		for index in link_indices:
			link = self.graph.links_by_index[index]
			link.flows.append((rtt, bandwidth))


	def apply_bandwidth(self):
		INDICES = 0
		RTT = 0
		BW = 1
		AGE = 2

		# First update the graph with the information of the flows
		active_links = []

		# Add the info about our flows
		for path in self.active_paths:
			for link in path.links:
				active_links.append(link)
				link.flows.append((path.RTT, path.used_bandwidth))

		# Add the info about others flows
		to_delete = []
		for key in self.flow_accumulator:
			flow = self.flow_accumulator[key]

			# TODO recheck age of flows, old packets
			if flow[AGE] < EmulationCore.MAX_FLOW_AGE:
				link_indices = flow[INDICES]
				self.apply_flow(flow)
				for index in link_indices:
					active_links.append(self.graph.links_by_index[index])

				flow[AGE] += 1

			else:
				to_delete.append(key)
		
		
		# print_named("FAIL", f"{len(self.active_paths_ids)}")
		
		
		# Now apply the RTT Aware Min-Max to calculate the new BW
		for id in self.active_paths_ids:
			path = self.graph.paths_by_id[id]
			with path.lock:
				max_bandwidth = path.max_bandwidth
				for link in path.links:
					rtt_reverse_sum = 0
					for flow in link.flows:
						rtt_reverse_sum += (1.0 / flow[RTT])
						
					max_bandwidth_on_link = []
					# calculate our bandwidth
					max_bandwidth_on_link.append(((1.0 / link.flows[0][RTT]) / rtt_reverse_sum) * link.bandwidth_bps)
					
					# Maximize link utilization to 100%
					spare_bw = link.bandwidth_bps - max_bandwidth_on_link[0]
					our_share = max_bandwidth_on_link[0] / link.bandwidth_bps
					hungry_usage_sum = our_share  # We must be before the loop to avoid division by zero
					for i in range(1, len(link.flows)):
						flow = link.flows[i]
						# calculate the bandwidth for everyone
						max_bandwidth_on_link.append(((1.0 / flow[RTT]) / rtt_reverse_sum) * link.bandwidth_bps)

						# Check if a flow is "hungry" (wants more than its allocated share)
						if flow[BW] > max_bandwidth_on_link[i]:
							spare_bw -= max_bandwidth_on_link[i]
							hungry_usage_sum += max_bandwidth_on_link[i] / link.bandwidth_bps
						else:
							spare_bw -= flow[BW]
							
					normalized_share = our_share / hungry_usage_sum  # we get a share of the spare proportional to our RTT
					maximized = max_bandwidth_on_link[0] + (normalized_share * spare_bw)
					if maximized > max_bandwidth_on_link[0]:
						max_bandwidth_on_link[0] = maximized

					# If this link restricts us more than previously try to assume this bandwidth as the max
					if max_bandwidth_on_link[0] < max_bandwidth:
						max_bandwidth = max_bandwidth_on_link[0]
						
				
				if max_bandwidth <= path.max_bandwidth and max_bandwidth != path.current_bandwidth:
					if max_bandwidth <= path.current_bandwidth:
						path.current_bandwidth = max_bandwidth  # if its less then we now for sure it is correct
					else:
						#  if it is more then we have to be careful, it might be a spike due to lost metadata
						path.current_bandwidth = EmulationCore.ONE_MINUS_ALPHA * path.current_bandwidth + \
												 EmulationCore.ALPHA * max_bandwidth
					
					src_service = path.links[0].source
					dst_service = path.links[-1].destination
					
					
					# FIXME
					print_named("cb", f"{src_service.ip} -> {dst_service.ip}, bw {int(path.current_bandwidth/1000)}")
					
					# PathEmulation.change_bandwidth(service, path.current_bandwidth)
					self.manager_lib.changeBandwidth(src_service.ip, dst_service.ip, int(path.current_bandwidth/1000))
					
					
					
		# clear the state on the graph
		for link in active_links:
			link.flows.clear()

		# delete old flows outside of dictionary iteration
		for key in to_delete:
			del self.flow_accumulator[key]
			
	
	def check_active_flows(self):
		current_time = time()
		self.check_flows_time_delta = current_time - self.last_time
		self.last_time = current_time
		
		self.manager_lib.pullFlows()
		
		
	def collect_own_flow(self, src_ip, dst_ip, sent_bytes, qlen):
		
		src_host = self.graph.hosts_by_ip[src_ip]
		dst_host = self.graph.hosts_by_ip[dst_ip]
		
		# Calculate current throughput
		if sent_bytes < dst_host.last_bytes:
			bytes_delta = sent_bytes  # in case of overflow ignore the bytes before the overflow
		else:
			bytes_delta = sent_bytes - dst_host.last_bytes
			
		bits = bytes_delta * 8
		throughput = bits / self.check_flows_time_delta
		dst_host.last_bytes = sent_bytes
		
		# Get the network path
		if dst_host in self.graph.paths[src_host]:  # some services are not reachable, test for that
			path = self.graph.paths[src_host][dst_host]
			
			# Check if this is an active flow
			if throughput <= (path.max_bandwidth * EmulationCore.ERROR_MARGIN) / 1000:
				path.used_bandwidth = 0
				
				print_message(f" FAIL {src_ip} -> {dst_ip} :: {throughput} <= {path.max_bandwidth * EmulationCore.ERROR_MARGIN}")
				return
			
			# This is an active flow (check flows without the dashboard)
			msg = "\n" + src_host.name + "--" + dst_host.name + ":" + str(throughput) + "\n"
			msg += "going through links: "
			for link in path.links:
				msg += link.source.name + "--" + link.destination.name + ", "
			print_message(msg)
			
			path.used_bandwidth = throughput
			self.active_paths.append(path)
			self.active_paths_ids.append(path.id)
			
			
			# # CHANGED PG alternative place to add flows
			# self.comms.add_flow(int(throughput), [link.index for link in path.links])

		
	def accumulate_flow(self, bandwidth, link_indices, age=0):
		"""
		This method adds a flow to the accumulator (Note: it doesnt grab the lock)
		:param bandwidth: int
		:param link_indices: List[int]
		:param age: int
		"""
		key = str(link_indices[0]) + ":" + str(link_indices[-1])
		if key in self.flow_accumulator:
			flow = self.flow_accumulator[key]
			flow[1] = bandwidth		# flow.bandwidth
			flow[2] = age			# flow.age
		else:
			self.flow_accumulator[key] = [link_indices, bandwidth, age]
	
	
	# link_indices contains the indices of all links on a given path with that bandwidth
	# ie. len(link_indices) = # of links in path
	def collect_flow(self, bandwidth, link_indices, age=0):
		"""
		This method collects a flow from other nodes, it checks if it is interesting and if so calls accumulate_flow
		:param bandwidth: int
		:param link_indices: List[int]
		:param age: int
		"""
		# TODO the return value is no longer useful
		
		# Check if this flow is interesting to us
		with self.state_lock:
			self.accumulate_flow(bandwidth, link_indices, age)
		return True


