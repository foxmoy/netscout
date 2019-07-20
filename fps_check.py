#!/usr/bin/env python
__author__ = 'bernied'

import datetime
import geoip2.database
import requests

import json
import signal
import sys
import time


def _shutdown(signum, frame):
    """
    Common function for shutting down ...
    """

    print('Shutting down')
    #print last_30_secs_flows
    sys.exit(0)

# Set up signal handlers
signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGABRT, _shutdown)
# ^C shuts down
signal.signal(signal.SIGINT, _shutdown)

try:
    stream_request = requests.get('http://54.190.154.136:8080/fps', stream=True)
except Exception as e:
    print "Error connecting to http://54.190.154.136:8080/fps"
    sys.exit(1)

try:
    db_reader = geoip2.database.Reader('./GeoLite2-Country_20190430/GeoLite2-Country.mmdb')
except Exception as e:
    print "GeoLite2 DB is not readable"
    sys.exit(2)

country_fps_current = {}
country_fps_prev = {}
last_30_secs_flows = []
start_time = 0

def print_anomalies_every_30s():
    """
    Method called every 30 seconds from main loop to print out anomalies
    """
    global country_fps_current, country_fps_prev

    print "current time: %s" % datetime.datetime.now()

    for src_country, flow_count  in country_fps_current.items():

        # if previous fps data is just initialized, skip
        if country_fps_prev[src_country] == 0:
            continue

        # compare to previous 30sec period.
        # These +50% and -34% thresholds seemed reasonable for just barely detecting anomalies
        # Could be improved with more complicated lookbacks, looking back farther than the
        # previus 30s period.
        if (float(country_fps_current[src_country]) / country_fps_prev[src_country] > 1.5) or \
                (float(country_fps_current[src_country]) / country_fps_prev[src_country] < 0.66):
            print "Country: %s" % src_country

        # Perhaps print out or act on individual netflows contained in last_30_sec_flows?

    # store current for reference during next 30 second call of this method.
    country_fps_prev = country_fps_current

    # zeroize current's counters.
    country_fps_current = country_fps_current.fromkeys(country_fps_current, 0)


print "Anomalies for at least 30s:"

for line in stream_request.iter_lines():
    if not start_time:
        # set start time of the 30 second period
        start_time = time.time()

    if not line:
        continue
    try:
        data = json.loads(line)

    # under rare ocassions, data didn't contain the closing } required for valid JSON.
    # Given the rarity and thresholds used, I think it's ok to skip the invalid data
    except Exception as e:
        continue

    src_ip = data["src_ip:src_port"].split(':')[0]

    # look up flow source ip in DB
    response = db_reader.country(src_ip)
    src_country = response.country.name
    data["src_country"] = src_country

    # Dictionary init
    if not country_fps_current.has_key(src_country): 
        country_fps_current[src_country] = 0
    if not country_fps_prev.has_key(src_country):
        country_fps_prev[src_country] = 0

    # Since the netflows contain a "flows" element, add those to that country's totals
    country_fps_current[src_country] = country_fps_current[src_country] + data["flows"]

    last_30_secs_flows.append(data)

    current_time = time.time();

    # Is it time to print out anomalies?
    if (current_time - start_time > 30):
        print_anomalies_every_30s()
        start_time = 0
