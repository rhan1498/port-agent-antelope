#!/usr/bin/env python

from cPickle import dumps

import gevent
from gevent import Greenlet, spawn

from cmdproc import CmdProcessor
from config import Config
import ntp
from packet import makepacket


STATES = [
    'STATE_UNKNOWN',
    'STATE_STARTUP',
    'STATE_UNCONFIGURED',
    'STATE_CONFIGURED',
    'STATE_CONNECTED',
    'STATE_DISCONNECTED',
]

BASE_FILENAME = "port_agent"


class COMMAND_SENTINEL(object): pass

class PortAgent(Greenlet):
    def __init__(self, options):
        super(PortAgent, self).__init__()
        self.options = options
        self.cmdproc = CmdProcessor()
        for val in self.__dict__.itervalues():
            if hasattr(val, '_is_a_command') and val._is_a_command is COMMAND_SENTINEL:
                self.cmdproc.setCmd(val.__name__, None, val)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, v):
        if v in STATES:
            self._state = v
            print "new state:", v
        else:
            raise Exception("Invalid state")

    def _run(self):
        self.state = 'STATE_STARTUP'
        self.cfg = Config(self.options, self.cmdproc)
        # start cmdserver; err if not cmd port
        spawn(self.state_unconfigured)

    def _cmd(f):
        f._is_a_command = COMMAND_SENTINEL
        return f

    @_cmd
    def get_state(self, sock):
        print "get_state"
        sock.sendall(makepacket(MSG_TYPE_STATUS, ntp.now(), self.state))

    @_cmd
    def ping(self, sock):
        print "ping"
        sock.sendall(makepacket(MSG_TYPE_HEARTBEAT, ntp.now(), ''))

    @_cmd
    def shutdown(self, sock):
        gevent.shutdown()

    def state_unconfigured(self):
        self.state = 'STATE_UNCONFIGURED'
        self.cfg.configuredevent.wait()
        spawn(self.state_configured)

    def state_configured(self):
        self.state = 'STATE_CONFIGURED'
        # spawn orbreapthr
        self.orbpktsrc = OrbPktSrc(
            srcname = cfg.antelope_orb_name,
            select = cfg.antelope_orb_select,
            reject = cfg.antelope_orb_reject,
            timeout = 1,
            transformation = dumps
        )
        self.orbpktsrc.start()
        # spawn data server
        self.dataserver = DataServer(self.cfg, self.orbpktsrc)
        self.dataserver.start()
        # spawn state_connected
        spawn(self.state_connected)

    def state_connected(self):
        self.state = 'STATE_CONNECTED'
        # on dataserver config update event
        self.cfg.dataserverconfgupdate.wait()
        self.orbreapthr.kill()
        self.dataserver.stop()
        spawn(self.state_configured)

    # no state_disconnected; orbreapthr doesn't ever disconnect or even report
    # errors; there are various approaches we could take to try to beat it into
    # shape, if necessary.

