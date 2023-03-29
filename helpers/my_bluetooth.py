import time
import struct
import numpy as np

import bluetooth
from bluetooth.btcommon import BluetoothError


class DataRecorder:
    def __init__(self):
        self.meditation = []
        self.attention = []
        self.raw = []
        self.blink = []
        self.poor_signal = []

        self.attention_queue = []
        self.meditation_queue = []
        self.poor_signal_queue = []
        self.blink_queue = []
        self.raw_queue = []

    def get_last_n_raw_second(self, n):
        ar = np.zeros(512*n)

        num = 0
        if len(self.raw) < 512*n:
            num = len(self.raw)
            ar[len(ar)-num:] = self.raw
        else: 
            num = len(self.raw)-512*n
            ar = self.raw[num:]

        ar = np.array(ar)
        ar[np.abs(ar) > 4000] = 0
        return ar
        # if len(self.raw)>= 512*n:
        #     return self.raw[len(self.raw)-512*n:] 
        # else:
        #     return self.raw
    
    def get_last_n_poor_signal(self, n):
        if len(self.poor_signal)>= 512*n:
            return self.poor_signal[len(self.poor_signal)-512*n:] 
        else:
            return self.poor_signal
    
    def get_last_n_blink(self, n):
        if len(self.blink)>= 512*n:
            return self.blink[len(self.blink)-512*n:] 
        else:
            return self.blink

    def cleanSlate(self):
        self.meditation = []
        self.attention = []
        self.raw = []
        self.blink = []
        self.poor_signal = []

        self.attention_queue = []
        self.meditation_queue = []
        self.poor_signal_queue = []
        self.blink_queue = []
        self.raw_queue = []

    def dispatch_data(self, key, value):
        if key == "attention":
            self.attention_queue.append(value)
            # Blink and "poor signal" is only sent when a blink or poor signal is detected
            # So fake continuous signal as zeros.
            
            
        elif key == "meditation":
            self.meditation_queue.append(value)
        elif key == "raw":
            # self.blink_queue.append(0)
            # self.poor_signal_queue.append(0)
            self.raw_queue.append(value)
        elif key == "blink":
            # self.blink_queue.append(value)
            if len(self.blink_queue)>0:
                self.blink_queue[-1] = value
 
        elif key == "poor_signal":
            if len(self.poor_signal_queue)>0:
                self.poor_signal_queue[-1] = value
     
    def record_meditation(self, attention):
        self.meditation_queue.append()
        
    def record_blink(self, attention):
        self.blink_queue.append()
    
    def finish_chunk(self):
        """ called periodically to update the timeseries """
        self.meditation += self.meditation_queue
        self.attention += self.attention_queue
        self.blink += self.blink_queue
        self.raw += self.raw_queue
        self.poor_signal += self.poor_signal_queue

        self.attention_queue = []
        self.meditation_queue = []
        self.poor_signal_queue = []
        self.blink_queue = []
        self.raw_queue = []

class DataParser(object):
    def __init__(self, recorder):
        self.recorder = recorder
        self.parser = self.parse()
        self.parser.__next__()

    def feed(self, data):
        for c in data:
            self.parser.send(ord(chr(c)))
        self.recorder.finish_chunk()
    
    def dispatch_data(self, key, value):
        self.recorder.dispatch_data(key, value)

    def parse(self):
        """
            This generator parses one byte at a time.
        """
        i = 1
        times = []
        while 1:
            byte = yield
            if byte== 0xaa:
                byte = yield # This byte should be "\aa" too
                if byte== 0xaa:
                    # packet synced by 0xaa 0xaa
                    packet_length = yield
                    packet_code = yield
                    if packet_code == 0xd4:
                        # standing by
                        self.state = "standby"
                    elif packet_code == 0xd0:
                        self.state = "connected"
                    elif packet_code == 0xd2:
                        data_len = yield
                        headset_id = yield
                        headset_id += yield
                        self.dongle_state = "disconnected"
                    else:
                        self.sending_data = True
                        left = packet_length - 2
                        while left>0:
                            if packet_code ==0x80: # raw value
                                row_length = yield
                                a = yield
                                b = yield
                                value = struct.unpack("<h",bytes([b, a]))[0]
                                self.dispatch_data("raw", value)
                                left -= 2
                            elif packet_code == 0x02: # Poor signal
                                a = yield
                                self.dispatch_data("poor_signal", a)
                                left -= 1
                            elif packet_code == 0x04: # Attention (eSense)
                                a = yield
                                if a>0:
                                    v = struct.unpack("b",bytes([a]))[0]
                                    if 0 < v <= 100:
                                        self.dispatch_data("attention", v)
                                left-=1
                            elif packet_code == 0x05: # Meditation (eSense)
                                a = yield
                                if a>0:
                                    v = struct.unpack("b",bytes([a]))[0]
                                    if 0 < v <= 100:
                                        self.dispatch_data("meditation", v)
                                left-=1
                                
                                
                            elif packet_code == 0x16: # Blink Strength
                                self.current_blink_strength = yield
                                self.dispatch_data("blink", self.current_blink_strength)
                                left-=1
                            elif packet_code == 0x83:
                                vlength = yield
                                self.current_vector = []
                                for row in range(8):
                                    a = yield
                                    b = yield
                                    c = yield
                                    value = a*255*255+b*255+c
                                left -= vlength
                                self.dispatch_data("bands", self.current_vector)
                            packet_code = yield
                else:
                    pass # sync failed
            else:
                pass # sync failed

def connect_bluetooth_addr(addr):
    for i in range(5):
        if i > 0:
            time.sleep(1)
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        try:
            sock.connect((addr, 1))
            sock.setblocking(False)
            return sock, addr
        except:
            print("ERROR!")
            return None, None
    return None, None

def start_headset(addr):
    socket, socketAddress = connect_bluetooth_addr(addr)
    failed = False
    
    if socket is None:
        failed = True

    for i in range(5):
        try:
            if i>0:
                print("Retrying...")
                time.sleep(1)
            len(socket.recv(10))
            break
        except BluetoothError:
            failed = True
        except:
            print('...')
        
        if i == 5:
            failed = True

    if failed:
        print('Failed')
        return None

    print(f"Connected to the headset at {socketAddress}")
    return socket

def search_blueetooth_devices():
    devices = bluetooth.discover_devices(lookup_names=True,lookup_class=True, duration = 1)
    return devices
