#!/usr/bin/env python

import gevent

from orbpktsrc import OrbPktSrc

s = OrbPktSrc('anfexport:prelim:', '.*', '')
s.start()

def clock():
    while True:
        print 'tick'
        gevent.sleep(0.25)

def subscriber():
    with s.subscription() as q:
        while True:
            print q.get()[:75]

gevent.spawn(clock)
gevent.spawn(subscriber)
gevent.wait()

