import kivy
kivy.require('2.0.0')

from kivy.config import Config

# Disable window resizing by the user
Config.set('graphics', 'resizable', '0')

# Set the window to open in full screen (matches your current display's resolution)
Config.set('graphics', 'fullscreen', 'auto')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ListProperty, ObjectProperty, StringProperty
)
from kivy.core.window import Window
import os
import struct
import datetime
import subprocess
from lib.xair import XAirClient, find_mixer
import sys

red = [.8, 0, 0, 1]
rred = [1, 0, 0, 1]
green = [0, .5, 0, 1]
ggreen = [0, .8, 0, 1]
blue = [0, 0, .5, 1]
bblue = [0, 0, .9, 1]
yellow = [.9, .9, 0, 1]
purple = [.9, 0, .9, 1]
orange = [1, .6, 0, 1]
white = [1, 1, 1, 1]
gray = [1, 1, 1, 1]
colors = [gray,rred,ggreen,yellow,bblue,purple,orange,white]
ratios = [1.1, 1.3, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10, 20, 100]

class ChannelData(BoxLayout):
    "Data structure to represent a Channel Meter Display"
    # labels to place left and right of the box
    in_text = StringProperty("Top")
    out_text = StringProperty("Mid")
    # color of the bar graph
    in_color = ListProperty(blue)
    out_color = ListProperty(red)
    post_color = ListProperty(green)
    # height of the bar as a percent of the box size
    in_percent = NumericProperty(1)
    out_percent = NumericProperty(1)
    post_percent = NumericProperty(0)
    # additional properties for the channel
    gain = StringProperty("0")
    ratio = StringProperty("0")
    thr = StringProperty("0")
    mgain = StringProperty("0")
    color = ListProperty(white)
    level = StringProperty("")
    level_out = StringProperty("")

    # meter values are sent as 16bit signed int mapped to -128db to 128db
    # 1/256 db resolution, aka .004 dB, values max at 0db
    def scale_value(self, value):
        "scales 16bit unsigned meter value for display"
        color = ggreen     # default color if good
        value = value/256  # convert to DB
        color = ggreen     # default color
        if value > -7:
            color = red    # close to clipping
        elif value < -17:
            color = bblue   # color if low
        if value < -27:
            color = blue  # color if very low

        value = value + 35  # shift by 35 DB to make the sale look right
        if value < 0:
            value = 0
        return (value / 35, color)  # scale to between 0 and 1

    def debug_value(self, value):
        value = value/256  # convert to DB and shift by 60 DB
        if value < -70:       #floor the value at -70 db
            return ""
        return f"{value:.1f} dB"

    #updated meter value based on 16 bit unsigned value showing
    #-128db to +128db in db/256 increments
    def update_in(self, value):
        (self.in_percent, self.in_color) = self.scale_value(value)
#        self.level = self.debug_value(value)

    def update_out(self, value):
        (self.out_percent, self.out_color) = self.scale_value(value)
        self.level = self.debug_value(value)

    def update_post(self, value):
        (self.post_percent, self.post_color) = self.scale_value(value)
        self.level_out = self.debug_value(value)

class XRemGUI(Widget):
    channels = ObjectProperty(None) # kivy storage for channels
    buses = ObjectProperty(None)    # kivy storage for buses
    xair_button = ObjectProperty(None) # kivy storage for button
    channel_data = []               # python storage for channels and buses
    # xair connection info
    xair_address = None
    xair_client = None

    # setup for recording xair audio
    rec_proc = 0
    my_env = os.environ.copy()
    my_env['AUDIODEV'] = 'plughw:CARD=X18XR18'
    record_command = ['rec', '-q', '-c', '18', '-b', '24']
#    record_command = ['rec', '-c', '18', '-b', '24']
    record_file = ""
 
    def paint_buttons(self):
        for x in range(16):     # Create the 16 channels strips.
            self.channel_data.append(ChannelData(in_text = f'{x+1}',
                                    out_text = f'Ch {x+1}'))
            self.channels.add_widget(self.channel_data[x])

        self.channel_data.append(ChannelData(in_percent = 0, 
                                in_text = f'Aux L', 
                                out_text = f'Aux R'))
        self.buses.add_widget(self.channel_data[16])

        for x in range(3):      # Create 6 Output Bus
            self.channel_data.append(ChannelData(in_percent = 0,
                                    in_text = f'Bus {2*x+1}', 
                                    out_text = f'Bus {2*x+2}'))
            self.buses.add_widget(self.channel_data[17+x])

        self.channel_data.append(ChannelData(in_color = [0,0,0,1], 
                                in_text = f'Main L', 
                                out_text = f'Main R'))
        self.buses.add_widget(self.channel_data[20])

# the meter subscription is setup in the xair_client in the refresh method that runs
# every 5s a subscription sends values every 50ms for 10s
#
# meters 1 chanel (in): channels, aux_in, fx, aux_out, fx_send, main, monitor
# meters 2 input in, aux in, usb in
# meters 5 aux out, main out, ultranet out, usb out, phones out
    def received_meters(self, addr, *data):
        "receive an OSC Meters packet"
        meter_num = int(addr.split('/',)[-1]) # last element of OSC path
        data_size = struct.unpack("<L", data[0][0:4])[0]
        for i in range(data_size):
            value = struct.unpack("<h", data[0][(4+(i*2)):4+((i+1)*2)])[0]

            if meter_num == 2:   # inputs
                if i < 16:       # 16 inputs and 2 Aux
                    self.channel_data[i].update_in(value)
                if i == 16:       # Aux L
                    self.channel_data[i].update_out(value)
                if i == 17:       # Aux R
                    self.channel_data[i-1].update_post(value)
#            elif meter_num == 1: # channel input
#                if i > 15:       # skip 16 inputs
#                   if i < 17:       # Aux L
#                        self.channel_data[i].update_out(value)
#                   elif i < 18:       # Aux R
#                        self.channel_data[i-1].update_post(value)
            elif meter_num == 5: # outputs
                if i < 8:        # aux_out, main
                    bus_num = int(i/2)
                    ch_num = 17 + bus_num
                    if i%2:
                        self.channel_data[ch_num].update_post(value)
                    else:
                        self.channel_data[ch_num].update_out(value)
                elif i < 24:
                    ch_num = i - 8
                    self.channel_data[ch_num].update_post(value)
                elif i < 40:
                    ch_num = i - 24
                    self.channel_data[ch_num].update_out(value)
            if i > 39:
                break
        # ignore other meter types

    def name_handler(self, addr, *data):
        "receive a channel/bus/aux name update"
        elements = addr.split('/') # first three parts of the OSC path
        if data[0] != "":
            if elements[1] == "ch":
                ch_num = int(elements[2])
                self.channel_data[ch_num - 1].in_text = data[0]
            elif elements[1] == "bus":
                bus = int(elements[2])
                ch_num = int((bus - 1)/2) + 17
                if int(bus - 1)%2:
                    self.channel_data[ch_num].out_text = data[0]
                else:
                    self.channel_data[ch_num].in_text = data[0]
            elif elements[1] == "rtn" and elements[2] == "aux":
                self.channel_data[16].in_text = "%s L" % data[0]
                self.channel_data[16].out_text = "%s R" % data[0]
        # ignore other names

    def color_handler(self, addr, *data):
        "receive a channel/bus/aux color update"
        elements = addr.split('/') # first three parts of the OSC path
        if data[0] != "":
            if elements[1] == "ch":
                ch_num = int(elements[2])
                self.channel_data[ch_num - 1].color = colors[int(data[0])%8]
        # ignore other colors

    def dynamics_handler(self, addr, *data):
        "receive a channel/bus/aux dynamics update"
        elements = addr.split('/') # first three parts of the OSC path
        if data[0] != "":
            bus = 0
            if elements[1] == "ch":
                ch_num = int(elements[2]) - 1
            elif elements[1] == "bus":
                bus = int(elements[2])
                ch_num = int((bus - 1)/2) + 17
            elif elements[1] == "lr":
                ch_num = 16
            else:
                return
#            print(f" dynamics update: ch {ch_num}, {elements[3]}, {data}", file=sys.stderr)
            if elements[4] == "mgain":
                if bus in (1, 3, 5):
                    # won't happen as mgain isn't sent by bus
                    self.channel_data[ch_num].gain = f"mg {float(data[0])*24:.1f}"
                else:
                    self.channel_data[ch_num].mgain = f"mg {float(data[0])*24:.1f}"
                return
            elif elements[4] == "thr":
                if bus in (1, 3, 5):
                    self.channel_data[ch_num].gain = f"th {float(data[0])*60-60:.1f}"
                else:
                    self.channel_data[ch_num].thr = f"th {float(data[0])*60-60:.1f}"
                return
            elif elements[4] == "ratio":
                if bus in (1, 3, 5):
                    self.channel_data[ch_num].mgain = f"r {ratios[int(data[0])]}"
                else:
                    self.channel_data[ch_num].ratio = f"r {ratios[int(data[0])]}"
                return
        # ignore other dynamics

    def scale_fader(self, data):
        "convert fader float to dB"
        f = float(data)
        if f < 0.0625:
            d = (480 * f) - 90
        elif f < 0.25:
            d = (160 * f) - 70
        elif f < 0.5:
            d = (80 * f) - 50
        else:
            d = (40 * f) - 30
        if d < -90: 
            d = -90
        if d > 10:
            d = 10
        return d

    def lr_handler(self, addr, *data):
        "receive a lr update"
        elements = addr.split('/') # first three parts of the OSC path
        if data[0] != "":
            ch_num = 20
            if elements[3] == "fader":
                self.channel_data[20].gain = f"f {self.scale_fader(data[0]):.1f}"
                self.channel_data[20].mgain = ""
            elif elements[3] == "thr":
                self.channel_data[ch_num].thr = f"th {float(data[0])*60-60:.1f}"
            elif elements[3] == "ratio":
                self.channel_data[ch_num].ratio = f"r {ratios[int(data[0])]}"
            return
    
    def fader_handler(self, addr, *data):
        "receive a fader update"
        elements = addr.split('/') # first three parts of the OSC path
        if data[0] != "":
            if elements[1] == "rtn" and elements[2] == "aux" and elements[3] == "mix":
                self.channel_data[16].mgain = f"f {self.scale_fader(data[0]):.1f}"
                self.channel_data[16].thr = ""
                self.channel_data[16].ratio = ""
            return

    def headamp_handler(self, addr, *data):
        "receive a headamp update"
        elements = addr.split('/') # first three parts of the OSC path
        if data[0] != "":
            if elements[3] == "gain":
                ch_num = int(elements[2])
                if ch_num < 17:
                    self.channel_data[ch_num -1].gain = f"g {float(data[0])*72-12:.1f}"
                else:
                    self.channel_data[ch_num -1].gain = f"g {float(data[0])*32-12:.1f}"

    def connect_mixer(self, state):
        if state: # == "down":
            if self.xair_client is not None:
                return True
            self.quit_called = False
            # determine the mixer address
            if self.xair_address is None:
                self.xair_address = find_mixer()
                if self.xair_address is None:
                    print('Error: Could not find any mixers in network.',
                        'Using default ip address.')
                    self.xair_address = "192.168.50.146"

            # setup other modules
            self.xair_client = XAirClient(self.xair_address, self)
            self.xair_client.start_connection()
            if self.quit_called:
                self.xair_client = None
                return False
            return True
        else:
            if self.xair_client is not None:
                self.xair_client.stop_server()
                self.xair_client = None

    def record(self, state):
        print("record start %s" % state)
        if state: # == "down":
            print("mid %s" % self.rec_proc)
            print(self.record_command)
            if self.rec_proc == 0:
                print("starting %s" % state)
#                    self.record_file = '/media/pi/ExternalSSD/%s.caf' % \
                self.record_file = '/home/pi/recordings/%s.caf' % \
                        datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
                print(self.record_file)
                self.rec_proc = subprocess.Popen(self.record_command + \
                        [self.record_file], env=self.my_env)
                print(self.record_command + \
                        [self.record_file])
#                except OSError:
#                    print("Error")
#                    if self.rec_proc is not None:
#                       self.rec_proc.terminate()
        else:
            print("stopping")
            if self.rec_proc != 0:
                self.rec_proc.terminate()

    def quit(self):
        self.quit_called = True
        try:
            if self.rec_proc != 0:
                self.rec_proc.terminate()
            if self.xair_client is not None:
                self.xair_client.stop_server()
                self.xair_client = None
            exit()
        except:
            exit()


class Xrem(App):
    def build(self):
        Window.top = 0
        Window.left = 0
        self.GUI = XRemGUI()
        self.GUI.paint_buttons()
        return self.GUI


if __name__ == '__main__':
    Xrem().run()