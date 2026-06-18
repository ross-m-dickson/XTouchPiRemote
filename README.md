# XTouchPiRemote
RaspberryPi based extension to XTouch for XAir

The goal of this project is to use a Raspberry Pi to add functionality to a Behringer XTouch control surface when controlling a Behringer XAir Digital Mixer, specifically an XR18. This is loosely based on https://github.com/peterdikant/xair-remote as filtered through my fork at https://github.com/ross-m-dickson/xair-remote . This is setup as a seperate repo rather than a branch or fork as I'm diverging in almost all respects from the original other than general intent of connecting to the XAir.

The key functionality is to gather all the meters the XTouch either doesn't show or hides deep in the interface onto a single screen.

## Requirements

This project is based on the assumption of a full Python envionment and uses the Kivy GUI framework. As such it is probably cross platform but from a design perspective I've targeted Raspberry Pi 4 with Adafruit Raspberry Pi 7in touch screen with a secondary target of Raspberry Pi 3 with Adafruit PitFT 2.8 inch touch screen. I hope to test with Raspberry Pi Zero if I can get my hands on one.

Follow the usual instruction at Kivy.org including setting up a virtual environment for the baseline install.

## Running

Activate your virtual environment then run

    $ python main.py

## Details

The UI shows the regular 16 input channels in two banks on 8 on the left with control buttons, the Aux input, and all the outputs on the left.

Each input channel has a DB scale, shows the scribble strip for the channel, the input gain, the compresser make up gain, the compresser threashold, and the compresser ration. Underneith it shows three meters from left to right: input, pre fader, and output. These meters are color codes, dark blue for below -50 meaning essentially inaudible, blue for below -30 meaning a little low, green for below -5, and red above.

The Aux in and output busses have two meters each showing the post fader level.

The Aux in show input gain and fader level.

The output busses show compresser threshold and ratio.

The Main LR output shows fader level, compresser threadhold and ratio.

Channel names and colors are driven by the scribble strip settings. Lt Blue is mapped to Orange and Gray, Black, and White are all mapped to White. 