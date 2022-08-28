import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ListProperty, ObjectProperty, StringProperty
)
from kivy.vector import Vector
from kivy.clock import Clock
from kivy.core.window import Window
from random import randint

# Data structure to represent a Channel Strip
class GraphBox(BoxLayout):
    # color of the bar graph
    bar_color = ListProperty([0, 0, 0, 1])
    # height of the bar as a percent of the box size
    percent = NumericProperty(1)
    # lebels to place top middle and bottom of the box
    top_text = StringProperty("Top")
    mid_text = StringProperty("Mid")
    bot_text = StringProperty("Bot")

class PongBall(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


class XRemGUI(Widget):
    ball = ObjectProperty(None)
    channels = ObjectProperty(None)
    names = ("Bass", "Guitar", "Keys", "Keys", "Sax", "Don", "Kick", "Snare",
             "Raluca", "Ors",  "Itai", "Butch", "Ross", "Guest", "OL", "OR")
    mic = ("1/4", "1/4", "1/4", "1/4", "pga", "pga", "pga", "58",
           "58", "ors", "Sms", "M80", "LCT", "", "040", "040")
    channel_graphs = [None] * 16
 
    def paint_buttons(self):
        # Create the represetnations of the 16 channels strips (GraphBox)
        # the display has a channel number at top, a channel name in the middle
        # and a mic type at the bottom. There is an overlay of a bar graph.
        for x in range(16):
            self.channels.add_widget(GraphBox(bar_color = [1,0,0,1], 
            percent = x/16, top_text = f'{x+1}', mid_text = self.names[x], 
            bot_text = self.mic[x]))

        for x in range(8):
            self.second.add_widget(GraphBox(bar_color = [1,0,0,1], 
            percent = x/8, top_text = self.names[x], mid_text = "B", bot_text = "C"))

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
        
        self.channels.children[3].percent = self.ball.y / self.height


class Xrem(App):
    def build(self):
        Window.top = 0
        Window.left = 0
        GUI = XRemGUI()
        GUI.paint_buttons()
        GUI.serve_ball()
        Clock.schedule_interval(GUI.update, 1.0 / 60.0)
        return GUI


if __name__ == '__main__':
    Xrem().run()