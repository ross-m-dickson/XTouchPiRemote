"This modules managed communications with the XAir mixer"
# part of xair-remote.py
# Copyright (c) 2018, 2021 Peter Dikant
# Additions Copyright (c) 2021 Ross Dickson
# Some rights reserved. See LICENSE.

import time
import threading
import socket
import netifaces
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer
from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

class OSCClientServer(BlockingOSCUDPServer):
    "The OSC communications agent"
    def __init__(self, address, dispatcher):
        super().__init__(('', 0), dispatcher)
        self.xr_address = address

    def send_message(self, address, value):
        "Packs a message for sending via OSC over UDB."
        builder = OscMessageBuilder(address=address)
        if value is None:
            values = []
        elif isinstance(value, list):
            values = value
        else:
            values = [value]
        for val in values:
            builder.add_arg(val)
        msg = builder.build()
        self.socket.sendto(msg.dgram, self.xr_address)

class XAirClient:
    """
    Handles the communication with the X-Air mixer via the OSC protocol
    """
    _CONNECT_TIMEOUT = 0.5
    _WAIT_TIME = 0.002
    _REFRESH_TIMEOUT = 5

    XAIR_PORT = 10024

    info_response = []

    def __init__(self, address, state):
        self.state = state
        dispatcher = Dispatcher()
        dispatcher.map("/meters/*", self.state.received_meters)
        dispatcher.map("/xinfo", self.msg_handler)
        dispatcher.map("/-*", self.null_handler)
        dispatcher.map("/rtn*", self.null_handler)
        dispatcher.map("/*/*/config/name", self.state.name_handler)
        dispatcher.set_default_handler(self.msg_handler)
        self.server = OSCClientServer((address, self.XAIR_PORT), dispatcher)
        worker = threading.Thread(target=self.run_server)
        worker.daemon = True
        worker.start()

    def start_connection(self):
        "Confirm that the connection to the XAir is live, otherwise initiaties shutdown."
        self.send('/xinfo')
        time.sleep(self._CONNECT_TIMEOUT)
        if len(self.info_response) > 0:
            print('Successfully connected to %s with firmware %s at %s.' % (self.info_response[2],
                    self.info_response[3], self.info_response[0]))
            # now start polling refresh /xremote command while running
            xair_thread = threading.Thread(target=self.refresh_connection)
            xair_thread.daemon = True
            xair_thread.start()

            # read_initial_state
            for channel in range(16):
                self.send('/ch/{:0>2d}/config/name'.format(channel + 1))
                time.sleep(self._WAIT_TIME)
            for channel in range(6):
                self.send('/bus/{:0>1d}/config/name'.format(channel + 1))
                time.sleep(self._WAIT_TIME)
            self.send('/rtn/aux/config/name')
            time.sleep(self._WAIT_TIME)

        else:
            print('Error: Failed to setup OSC connection to mixer.',
                  'Please check for correct ip address.')
            self.state.quit_called = True
            if self.server is not None:
                self.server.shutdown()
                self.server = None

    def run_server(self):
        "Start the OSC communications agent in a seperate thread."
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            self.stop_server()

    def stop_server(self):
        if self.server is not None:
            self.server.shutdown()
            self.server = None
        # not needed for xair_thread which reads quit_called

    def null_handler(self, addr, *data):
        "Drop known irrelevant OSC messages."
        pass

    def msg_handler(self, addr, *data):
        "Dispatch received OSC messages based on message type."
        if self.state is None or self.state.quit_called:
            self.stop_server()
            return
        if addr == '/xinfo':
            self.info_response = data[:]
        else:
            print('OSCReceived("%s", %s)' % (addr, data))

    def refresh_connection(self): # the thread to ping the XAir every _REFRESH_TIMEOUT
        """
        Tells mixer to send changes in state that have not been received from this OSC Client
          /xremote        - all parameter changes are broadcast to all active clients (Max 4)
          /xremotenfb     - No Feed Back. Parameter changes are only sent to the active clients
                                                                which didn't initiate the change
        """
        try:
            while not self.state.quit_called and self.server is not None:
                self.server.send_message("/xremotenfb", None)
                self.send(address="/meters", param=["/meters/1"])
                self.send(address="/meters", param=["/meters/2"])
                self.send(address="/meters", param=["/meters/5"])
                time.sleep(self._REFRESH_TIMEOUT)
                if self.state.quit_called:
                    self.stop_server()
                    return
        except socket.error:
            self.stop_server()

    def send(self, address, param=None):
        "Call the OSC agent to send a message"
        self.server.send_message(address, param)

def find_mixer():
    "Search for the IP address of the XAir mixer"
    print('Searching for mixer...')
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
    client.settimeout(5)
    for iface in netifaces.interfaces():
        try:
            bcast = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['broadcast']
            client.sendto("/xinfo\0\0".encode(), (bcast, XAirClient.XAIR_PORT))
        except:
            pass
    try:
        response = OscMessage(client.recv(512))
    except socket.timeout:
        print('No server found')
        return None
    client.close()

    if response.address != '/xinfo':
        print('Unknown response')
        return None
    else:
        print('Found ' + response.params[2] + ' with firmware ' + response.params[3] + ' on IP ' + response.params[0])
        return response.params[0]
