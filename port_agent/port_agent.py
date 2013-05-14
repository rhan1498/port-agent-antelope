#!/usr/bin/env python

from cPickle import dumps

import gevent
from gevent import Greenlet, spawn

from ooi.logging import log

from cmdproc import CmdProcessor
from config import Config
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
            log.debug("Transitioning to state %s" % v)
        else:
            raise Exception("Invalid state", v)

    def _run(self):
        try:
            state = self.state_startup
            while True:
                log.debug("Transitioning to state %s" % state)
                state = state()
        except Exception:
            log.critical("PortAgent terminated due to exception", exc_info=True)
            raise

    def state_startup(self):
        self.cfg = Config(self.options, self.cmdproc)
        # start cmdserver; err if not cmd port
        assert self.cfg.command_port is not None
        self.cmdserver = CmdServer(self.cfg, self.cmdproc)
        self.cmdserver.start()
        # Is this bad? Do the parents stay alive forever, creating an infinite
        # recursion?
        # No, every Greenlet has it's parent set to hub
        # https://github.com/surfly/gevent/blob/master/gevent/greenlet.py#L76
        return self.state_unconfigured

    def state_unconfigured(self):
        self.cfg.configuredevent.wait()
        return self.state_configured

    def orbreapthr_janitor(self, orbpktsrc):
        self.kill(orbpktsrc.exception)

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
        self.orbpktsrc.link(self.orbreapthr_janitor)
        self.orbpktsrc.start()
        # spawn data server
        self.dataserver = DataServer(self.cfg, self.orbpktsrc)
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

