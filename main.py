import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ListProperty, ObjectProperty, StringProperty
)
from kivy.core.window import Window
import os
import struct
from lib.xair import XAirClient, find_mixer


class ChannelData(BoxLayout):
    "Data structure to represent a Channel Meter Display"
    # labels to place left and right of the box
    in_text = StringProperty("Top")
    out_text = StringProperty("Mid")
    # color of the bar graph
    red = [.8, 0, 0, 1]
    blue = [0, 0, .5, 1]
    green = [0, .5, 0, 1]
    in_color = ListProperty(blue)
    out_color = ListProperty(red)
    post_color = ListProperty(green)
    # height of the bar as a percent of the box size
    in_percent = NumericProperty(1)
    out_percent = NumericProperty(1)
    post_percent = NumericProperty(0)

    # meter values are sent as 16bit signed int mapped to -128db to 128db
    # 1/256 db resolution, aka .004 dB, realistic values max at 0db
    def scale_value(self, value):
        "scales 16bit unsigned meter value for display"
        value = value/256 + 60  # convert to DB and shift by 60 DB
        if value < 0:       #floor the value at -60 db
            value = 0
        if value > 50:      # expand top 10 db into 20
            value = ((value - 50) * 2) + 50 
        color = self.green  # default color
        if value < 10:
            color = self.blue   # color if very low
        elif value > 62:
            color = self.red    # clipping
        return (value / 70, color)  # scale to between 0 and 1

    #updated meter value based on 16 bit unsigned value showing
    #-128db to +128db in db/256 increments
    def update_in(self, value):
        (self.in_percent, self.in_color) = self.scale_value(value)

    def update_out(self, value):
        (self.out_percent, self.out_color) = self.scale_value(value)

    def update_post(self, value):
        (self.post_percent, self.post_color) = self.scale_value(value)

class PongBall(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


class XRemGUI(Widget):
    channels = ObjectProperty(None) # kivy storage for channels
    buses = ObjectProperty(None)    # kivy storage for buses
    channel_data = []               # python storage for channels and buses
    # xair connection info
    xair_address = None
    xair_client = None

    # setup for recording xair audio
    rec_proc = None
    my_env = os.environ.copy()
    my_env['AUDIODEV'] = 'hw:X18XR18,0'
    record_command = ['rec', '-q', '--buffer', '262144', '-c', '18', '-b', '24']
    record_file = ""
 
    def paint_buttons(self):
        for x in range(16):     # Create the 16 channels strips.
            self.channel_data.append(ChannelData(in_text = f'{x+1}',
                                    out_text = f'Channel {x+1}'))
            self.channels.add_widget(self.channel_data[x])

        self.channel_data.append(ChannelData(in_text = f'Aux L', 
                                out_text = f'Aux R'))
        self.buses.add_widget(self.channel_data[16])

        for x in range(3):      # Create 6 Output Bus
            self.channel_data.append(ChannelData(in_percent = x/8,
                                    in_text = f'Bus {2*x+1}', 
                                    out_text = f'Bus {2*x+2}'))
            self.buses.add_widget(self.channel_data[17+x])

        self.channel_data.append(ChannelData(in_color = [1,0,0,1], 
                                in_text = f'Main L', 
                                out_text = f'Main R'))
        self.buses.add_widget(self.channel_data[20])

# the meter subscription is setup in the xair_client in the refresh method that runs
# every 5s a subscription sends values every 50ms for 10s
#
# meters 1 pre_fader: channels, aux_in, fx, aux_out, fx_send, main, monitor
# meters 2 input in, aux in, usb in
# meters 5 aux out, main out, ultranet out, usb out, phones out
    def received_meters(self, addr, data):
        "receive an OSC Meters packet"
        meter_num = int(addr.split('/',)[-1]) # last element of OSC path
        print("received meter %s" % meter_num) 
        data_size = struct.unpack("<L", data[0][0:4])[0]
        for i in range(data_size):
            value = struct.unpack("<h", data[0][(4+(i*2)):4+((i+1)*2)])[0]

            if meter_num == 2:   # inputs
                if i < 18:       # 16 inputs and 2 Aux
                    self.channel_data[i].update_in(value)
            elif meter_num == 1: # pre_fader
                if i < 18:       # 16 inputs and 2 Aux
                    self.channel_data[i].update_out(value)
            elif meter_num == 5: # outputs
                print("meter %s has value %s" % (i, value/256))
                if i < 8:        # aux_out, main
                    bus_num = int(i/2)
                    ch_num = 17 + bus_num
                    if i%2:
                        self.channel_data[ch_num].update_out(value)
                    else:
                        self.channel_data[ch_num].update_in(value)
                elif i < 24:
                    ch_num = i - 8
                    self.channel_data[ch_num].update_post(value)
            if i > 23:
                break
        # ignore other meter types

    def connect_mixer(self, state):
        if state == "down":
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
        if state == "down":
            if self.rec_proc is not None:
                try:
                    self.record_file = '/media/pi/ExternalSSD/%s.caf' % \
                        datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
                    self.rec_proc = subprocess.Popen(self.record_command + \
                        [self.record_file], env=self.my_env)
                except OSError:
                    if self.rec_proc is not None:
                        self.rec_proc.terminate()
        else:
            if self.rec_proc is not None:
                self.rec_proc.terminate()

    def quit(self):
        self.quit_called = True
        try:
            if self.rec_proc is not None:
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