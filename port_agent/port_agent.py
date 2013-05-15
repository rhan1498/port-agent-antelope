#!/usr/bin/env python

from cPickle import dumps

import gevent
from gevent import Greenlet, spawn, sleep
from gevent.event import Event

from ooi.logging import log

from servers import DataServer, CmdServer
import ntp
from orbpkt2dict import orbpkt2dict
from orbpktsrc import OrbPktSrc
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


def transform(orbpkt):
    d = orbpkt2dict(orbpkt)
    return dumps(d, 2)


class OrbPktSrcError(Exception): pass


class COMMAND_SENTINEL(object): pass

class PortAgent(Greenlet):
    def __init__(self, cfg, cmdproc):
        super(PortAgent, self).__init__()
        self.cfg = cfg
        self.cmdproc = cmdproc
        self.heartbeat_event = Event()
        for val in self.__dict__.itervalues():
            if hasattr(val, '_is_a_command') and val._is_a_command is COMMAND_SENTINEL:
                cmdproc.setCmd(val.__name__, None, val)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, v):
        self._state = v
        log.debug("Transitioning to state %s" % v)

    def janitor(self, src):
        log.debug("Janitor, cleanup aisle 12")
        self.kill(src.exception)

    def heartbeat_timer(self):
        try:
            while True:
                self.cfg.heartbeatactive.wait()
                sleep(self.cfg.heartbeat_interval)
                self.heartbeat_event.set()
                self.heartbeat_event.clear()
        except Exception:
            log.critical("heartbeat_timer terminating due to exception", exc_info=True)
            raise

    def _run(self):
        try:
            self.state = self.state_startup
            spawn(self.heartbeat_timer).link_exception(self.janitor)
            while True:
                self.state = self.state()
        except Exception:
            log.critical("PortAgent terminating due to exception", exc_info=True)
            raise
        finally:
            try: self.orbpktsrc.kill()
            except: pass
            try: self.dataserver.stop()
            except: pass
            try: self.cmdserver.stop()
            except: pass

    def state_startup(self):
        # start cmdserver; err if not cmd port
        self.cmdserver = CmdServer(('localhost', self.cfg.command_port),
                                   self.cmdproc.processCmds, self.janitor)
        self.cmdserver.start()
        return self.state_unconfigured

    def state_unconfigured(self):
        self.cfg.configuredevent.wait()
        return self.state_configured

    def state_configured(self):
        # spawn orbreapthr
        # link to it? what if it dies?
        self.orbpktsrc = OrbPktSrc(
            srcname = self.cfg.antelope_orb_name,
            select = self.cfg.antelope_orb_select,
            reject = self.cfg.antelope_orb_reject,
            timeout = 1,
            transformation = transform
        )
        self.orbpktsrc.link_exception(self.janitor)
        self.orbpktsrc.start()
        # spawn data server
        self.dataserver = DataServer(
                ('localhost', self.cfg.data_port),
                self.orbpktsrc.subscription,
                self.heartbeat_event, self.janitor)
        self.dataserver.start()
        # spawn state_connected
        return self.state_connected

    def state_connected(self):
        # on dataserver config update event
        self.cfg.dataserverconfigupdate.wait()
        self.orbreapthr.kill()
        self.dataserver.stop()
        return self.state_configured

    def _cmd(f):
        f._is_a_command = COMMAND_SENTINEL
        return f

    @_cmd
    def get_state(self, sock):
        sock.sendall(makepacket(MSG_TYPE_STATUS, ntp.now(), self.state))

    @_cmd
    def ping(self, sock):
        sock.sendall(makepacket(MSG_TYPE_HEARTBEAT, ntp.now(), ''))

    @_cmd
    def shutdown(self, sock):
        gevent.shutdown()

    # no state_disconnected; orbreapthr doesn't ever disconnect or even report
    # errors; there are various approaches we could take to try to beat it into
    # shape, if necessary.

