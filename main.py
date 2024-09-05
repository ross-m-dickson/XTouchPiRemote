import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ListProperty, ObjectProperty, StringProperty
)
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.core.window import Window
from random import randint
from collections import deque

import os
from lib.xair import XAirClient, find_mixer

class ChannelData(BoxLayout):
    "Data structure to represent a Channel Meter Display"
    # labels to place left and right of the box
    in_text = StringProperty("Top")
    out_text = StringProperty("Mid")
    # color of the bar graph
    in_color = ListProperty([1, 0, 0, 1])
    out_color = ListProperty([0, 0, .5, 1])
    # height of the bar as a percent of the box size
    in_percent = NumericProperty(1)
    out_percent = NumericProperty(1)

    # make the level display a 4 element running window
    values = 4
    def __init__(self, *args, **kwargs):
        self.levels = deque(maxlen=self.values)
        for _ in range(self.values):
            self.levels.append(-102400)
        self.mean = -102400 * self.values
        super().__init__(*args, **kwargs)

    def insert_level(self, value):
        'push a vlue into the fixed FIFO and update the mean'
        self.mean = self.mean - self.levels.popleft() + value
        self.levels.append(value)
        return self.mean


class PongBall(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


class XRemGUI(Widget):
    ball = ObjectProperty(None)
    # kivy storage for channels
    channels = ObjectProperty(None)
    # kivy storage for buses
    buses = ObjectProperty(None)
    # python storage for channels and buses
    channel_data = []
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
        # Create the represetnations of the 16 channels strips.
        # There is an overlay of a bar graph.
        for x in range(16):
            self.channel_data.append(ChannelData(in_color = [1,0,0,1],
                                    in_percent = x/16, in_text = f'{x+1}',
                                    out_text = f'Channel {x+1}'))
            self.channels.add_widget(self.channel_data[x])

        for x in range(8):
            self.channel_data.append(ChannelData(in_color = [1,0,0,1], 
                                    in_percent = x/8, in_text = f'Aux {2*x+1}', 
                                    out_text = f'Aux {2*x+2}'))
            self.buses.add_widget(self.channel_data[16+x])

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

    def serve_ball(self):
        self.ball.center = self.center
        self.ball.velocity = Vector(4, 0).rotate(randint(0,360))

    def update(self, dt):
        self.ball.move()

        # bounce off top and bottom
        if (self.ball.y < 0)  or (self.ball.top > self.height):
            self.ball.velocity_y *= -1

        # bounce off left and right
        if (self.ball.x < 0)  or (self.ball.right > self.width):
            self.ball.velocity_x *= -1
        
        self.channels.children[3].in_percent = self.ball.y / self.height
        self.channels.children[3].out_percent = self.ball.y / self.height / 2


class Xrem(App):
    def build(self):
        Window.top = 0
        Window.left = 0
        self.GUI = XRemGUI()
        self.GUI.paint_buttons()
        self.GUI.serve_ball()
        Clock.schedule_interval(self.GUI.update, 1.0 / 60.0)
        return self.GUI


if __name__ == '__main__':
    Xrem().run()