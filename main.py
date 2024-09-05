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


class ChannelLabels(BoxLayout):
    # lebels to place top middle and bottom of the box
    top_text = StringProperty("Top")
    mid_text = StringProperty("Mid")

class ChannelData(BoxLayout):
    "Data structure to represent a Channel Meter Display"
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
    channels = ObjectProperty(None)
    channel_labels = ObjectProperty(None)
    bus_labels = ObjectProperty(None)
    channel_data = []
    channel_label_data = []
    names = ("Bass", "Guitar", "Keys", "Keys", "Sax", "Don", "Kick", "Snare",
             "Raluca", "Ors",  "Itai", "Butch", "Ross", "Guest", "OL", "OR")
    channel_graphs = [None] * 16
 
    def paint_buttons(self):
        # Create the represetnations of the 16 channels strips.
        # There is an overlay of a bar graph.
        for x in range(16):
            self.channel_data.append(ChannelData(in_color = [1,0,0,1],
                                    in_percent = x/16))
            self.channels.add_widget(self.channel_data[x])
            self.channel_label_data.append(ChannelLabels(top_text = f'{x+1}',
                                    mid_text = self.names[x]))
            self.channel_labels.add_widget(self.channel_label_data[x])

        for x in range(8):
            self.channel_data.append(ChannelData(in_color = [1,0,0,1], 
            in_percent = x/8))
            self.second.add_widget(self.channel_data[16+x]),
            self.channel_label_data.append(ChannelLabels(top_text = f'{2*x+1}', 
                                    mid_text = f'{2*x+2}'))
            self.bus_labels.add_widget(self.channel_label_data[16+x])
    
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
        Clock.schedule_interval(GUI.update, 1.0 / 60.0)
        return GUI


if __name__ == '__main__':
    Xrem().run()