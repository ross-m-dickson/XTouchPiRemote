# XTouchPiRemote
RaspberryPi based XTouch Mini to XAir Bridge

The goal of this project is to use a Raspberry Pi to bridge between a Behringer XTouch Mini UBS Midi control surface and a Behringer XAir Digital Mixer, specifically an XR18. This is loosely based on https://github.com/peterdikant/xair-remote as filtered through my fork at https://github.com/ross-m-dickson/xair-remote . This is setup as a seperate repo rather than a branch or fork as I'm diverging in almost all respects from the original other than general intent of connecting the XTouch Mini to the XAir. The key resaon for the change is that in addition to changing all of the data structers I'm also changing the file struct which is difficult for me to do cleanly in git. Please see the other two repos for the history.

## Requirements

This project is based on the assumption of a full Python envionment and uses the Kivy GUI framework. As such it is probably cross platform but from a design perspective I've targeted Raspberry Pi 4 with Adafruit Raspberry Pi 7in touch screen with a secondary target of Raspberry Pi 3 with Adafruit PitFT 2.8 inch touch screen. I hope to test with Raspberry Pi Zero if I can get my hands on one.

Follow the usual instruction at Kivy.org including setting up a virtual environment for the baseline install.

## Running

Activate your virtual environment then run

    $ python main.py