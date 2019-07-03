
import sys
import struct
import socket
from threading import Thread, Lock
from _thread import interrupt_main

import need.NEEDlib.communications.TCALHandler as TCALHandler
from need.NEEDlib.utils import print_identified, print_error_named, print_named
from need.NEEDlib.utils import stop_experiment


class DashboardHandler:
    TCP_PORT = 7073

    STOP_COMMAND = 1
    SHUTDOWN_COMMAND = 2
    READY_COMMAND = 3
    START_COMMAND = 4
    ACK = 120


    def __init__(self, scheduler):
        self.stop_lock = Lock()

        self.dashboard_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.dashboard_socket.bind(('0.0.0.0', self.TCP_PORT))

        self.dashboard_thread = Thread(target=self.receive_dashboard_commands)
        self.dashboard_thread.daemon = True
        self.dashboard_thread.start()

        # self.graph = graph      # removed graph from handler, was used only for prints
        self.scheduler = scheduler


    def receive_dashboard_commands(self):
        received = 1
        produced = 2

        self.dashboard_socket.listen()
        while True:
            connection, addr = self.dashboard_socket.accept()
            connection.settimeout(5)
            try:
                data = connection.recv(1)
                if data:
                    command = struct.unpack("<1B", data)[0]

                    if command == self.STOP_COMMAND:
                        # TODO Stop is now useless, probably best to just replace with shutdown
                        connection.close()
                        with self.stop_lock:
                            print_named("DashboardHandler.graph", "Stopping experiment")

                    elif command == self.SHUTDOWN_COMMAND:
                        # print_identified(self.graph, "received shutdown command.")

                        msg = "packets: recv " + str(received) + ", prod " + str(produced)
                        print_identified("enforcer", msg)

                        connection.send(struct.pack("<3Q", produced, 50, received))
                        ack = connection.recv(1)

                        if len(ack) != 1:
                            # print_error_named(self.graph, "Bad ACK len:" + str(len(ack)))
                            connection.close()
                            continue

                        if struct.unpack("<1B", ack)[0] != self.ACK:
                            print_error_named(self, "Bad ACK, not and ACK" + str(struct.unpack("<1B", ack)))
                            connection.close()
                            continue

                        connection.close()

                        with self.stop_lock:
                            self.dashboard_socket.close()
                            TCALHandler.teardown()
                            # print_identified(self.graph, "shutting down.")
                            sys.stdout.flush()
                            sys.stderr.flush()
                            stop_experiment()
                            interrupt_main()

                        return

                    elif command == self.READY_COMMAND:
                        connection.send(struct.pack("<1B", self.ACK))
                        connection.close()

                    elif command == self.START_COMMAND:
                        connection.close()
                        self.scheduler.start()
                        # print_identified(self.graph, "starting experiment.")

            except OSError as e:
                continue  # Connection timed out (most likely)

