#!/usr/bin/env python3
from periphery import GPIO
import time
from flask import Flask
from flask import send_from_directory
from flask import request
from flask import redirect
from flask import render_template
from threading import Thread
import yaml
import os.path
import sys
import serial
import Adafruit_ADS1x15

class moisture(Thread):
    def __init__(self):
        super(moisture, self).__init__()
        self.adc = None
        self.init_adc()
        self.raspberry=0
        self.currant=0
        self.read()
    def init_adc(self):
        self.adc = Adafruit_ADS1x15.ADS1115()
    def read(self):
        try:
            self.raspberry = int(self.adc.read_adc(0, gain=1, data_rate=128))
            self.currant = int(self.adc.read_adc(1, gain=1, data_rate=128))
        except OSError:
            self.init_adc()
    def run(self):
        while True:
            self.read()
            time.sleep(2)
    def get_raspberry(self):
        return self.raspberry
    def get_currant(self):
        return self.currant

class pumps(Thread):
    def __init__(self):
        super(pumps, self).__init__()
        self.raspberry = GPIO(23, "out")
        self.raspberry.write(True)
        self.currant = GPIO(24, "out")
        self.currant.write(True)
        self.raspberry_counter = 0
        self.currant_counter = 0
        self.raspberry_state = False
        self.currant_state = False
        if not os.path.isfile('status.yaml'):
            self.store_yaml()
        self.read_yaml()
    def read_yaml(self):
        with open('status.yaml', 'r') as f:
            try:
                y = yaml.safe_load(f)
                self.raspberry_counter = int(y['raspberry_water'])
                self.currant_counter = int(y['currant_water'])
            except yaml.YAMLError as exception:
                print(exception)
    def store_yaml(self):
        with open('status.yaml', 'w') as f:
            yaml.dump({'raspberry_water':int(self.raspberry_counter), 'currant_water':int(self.currant_counter)}, f, default_flow_style=False)
    def increase_counter(self):
        if self.raspberry_state:
            self.raspberry_counter += 1
        if self.currant_state:
            self.currant_counter += 1
        if self.raspberry_state or self.currant_state:
            self.store_yaml()
    def get_counter_raspberry(self):
        return self.raspberry_counter
    def get_counter_currant(self):
        return self.currant_counter
    def set(self, pump, state=False):
        if pump == "raspberry":
            self.raspberry_state = state
            self.raspberry.write(not state)
        elif pump == "currant":
            self.currant_state = state
            self.currant.write(not state)
    def run(self):
        while True:
            self.increase_counter()
            time.sleep(1)

global m
m = moisture()
m.start()

global p
p = pumps()
p.start()

app = Flask(__name__)

@app.route('/metrics')
def metrics():
    global m
    ret = ""
    ret += "moisture_sensor{sensor=\"raspberry\"} "+str(m.get_raspberry())+"\n"
    ret += "moisture_sensor{sensor=\"currant\"} "+str(m.get_currant())+"\n"
    ret += "watering_seconds{pump=\"raspberry\"} "+str(p.get_counter_raspberry())+"\n"
    ret += "watering_seconds{pump=\"currant\"} "+str(p.get_counter_currant())+"\n"
    return ret

@app.route('/static/<path:path>')
def static_files():
    return send_from_directory('static', path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rasp_on', methods=['GET', 'POST'])
def rasp_on():
    p.set("raspberry", state=True)
    return ('', 204)

@app.route('/rasp_off', methods=['GET', 'POST'])
def rasp_off():
    p.set("raspberry", state=False)
    return ('', 204)

@app.route('/curr_on', methods=['GET', 'POST'])
def curr_on():
    p.set("currant", state=True)
    return ('', 204)

@app.route('/curr_off', methods=['GET', 'POST'])
def curr_off():
    p.set("currant", state=False)
    return ('', 204)

if __name__ == '__main__':
    app.run(debug=False, port=9102, host='0.0.0.0')

    #m = moisture()
    #m.start()

    #for i in range(10):
    #    print("currant: "+str(m.get_currant()))
    #    print("raspberry: "+str(m.get_raspberry()))
    #    time.sleep(1.5)

    #p = pumps()
    #time.sleep(10)
    #p.set("raspberry", state=True)
    #time.sleep(1)
    #p.set("raspberry", state=False)
    #p.set("currant", state=True)
    #time.sleep(4)
    #p.set("currant", state=False)
