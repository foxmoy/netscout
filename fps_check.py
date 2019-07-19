#!/usr/bin/env python
__author__ = 'bernied'

import geoip2.database
import requests

import datetime
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

stream_request = requests.get('http://54.190.154.136:8080/fps', stream=True)
db_reader = geoip2.database.Reader('./GeoLite2-Country_20190430/GeoLite2-Country.mmdb')
country_fps_current = {}
country_fps_prev = {}
last_30_secs_flows = []
start_time = 0

def print_anomalies_every_30s():
    global country_fps_current, country_fps_prev

    print "current time: %s" % datetime.datetime.now()

    for src_country, flow_count  in country_fps_current.items():
        if country_fps_prev[src_country] == 0:
            break

        # compare to previous 30sec period
        if (float(country_fps_current[src_country]) / country_fps_prev[src_country] > 1.1) or \
                (float(country_fps_current[src_country]) / country_fps_prev[src_country] < 0.9):
            print "Country: %s" % src_country

# uncomment if flows are desired
#            for flow in last_30_secs_flows:
#                if flow["src_country"] == src_country:
#                    print flow

    country_fps_prev = country_fps_current
    country_fps_current = country_fps_current.fromkeys(country_fps_current, 0)


print "Anomalies for at least 30s:"

for line in stream_request.iter_lines():
    if not start_time:
        start_time = time.time()

    if not line:
        continue
    data = json.loads(line)

    src_ip = data["src_ip:src_port"].split(':')[0]
    response = db_reader.country(src_ip)
    src_country = response.country.name
    data["src_country"] = src_country

    # Dictionary init
    if not country_fps_current.has_key(src_country): 
        country_fps_current[src_country] = 0
    if not country_fps_prev.has_key(src_country):
        country_fps_prev[src_country] = 0

    country_fps_current[src_country] = country_fps_current[src_country] + data["flows"]

    last_30_secs_flows.append(data)

    current_time = time.time();


    if (current_time - start_time > 30):
        print_anomalies_every_30s()
        start_time = 0
