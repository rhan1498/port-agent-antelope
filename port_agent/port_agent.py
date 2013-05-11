#!/usr/bin/env python

import sys
from optparse import OptionParser


STATE_UNKNOWN          = 0x00000000
STATE_STARTUP          = 0x00000001
STATE_UNCONFIGURED     = 0x00000002
STATE_CONFIGURED       = 0x00000003
STATE_CONNECTED        = 0x00000004
STATE_DISCONNECTED     = 0x00000005

DEFAULT_HEARTBEAT_INTERVAL = 0

BASE_FILENAME = "port_agent"

DEFAULT_LOG_DIR  = "/tmp"
DEFAULT_CONF_DIR = "/tmp"
DEFAULT_PID_DIR  = "/tmp"
DEFAULT_DATA_DIR = "/tmp"

OBS_TYPE_UNKNOWN       = 0x00000000
OBS_TYPE_STANDARD      = 0x00000001
OBS_TYPE_MULTI         = 0x00000002


DEFAULTS = dict(
    # Initalize Defaults
    conffile = None,
    single = False,
    verbose = False,
    command_port = None,
    data_port = None,
    kill = False,
    version = False,
    ppid = None,
    # For backward compatibility, observatory connection defaults to standard
    observatoryConnectionType = OBS_TYPE_STANDARD,
    heartbeatInterval = DEFAULT_HEARTBEAT_INTERVAL,
    piddir = DEFAULT_PID_DIR,
    logdir = DEFAULT_LOG_DIR,
    confdir = DEFAULT_CONF_DIR,
)



COMMAND_SENTINEL = object()

class PortAgent(object):

    def __init__(self, cfg):
        self.setState(STATE_STARTUP)
        self.cfg = PortAgentConfig(cfg)
        self.cfg.readConfig()
        for val in self.__dict__.itervalues():
            if hasattr(val, '_is_a_command') and val._is_a_command is COMMAND_SENTINEL:
                self.cmdproc.setCmd(val.__name__, None, val)

    def start(self):
        reactor.run()
        pass

    def setState(self, state):
        self._state = state

    def _cmd(f):
        f._is_a_command = COMMAND_SENTINEL
        return f

    @_cmd
    def get_state(self, protocol):
        print "get_state"

    @_cmd
    def ping(self, protocol):
        print "ping"

    @_cmd
    def shutdown(self, protocol):
        print "shutdown"



def main(args=None):
    if args is None:
        args = sys.argv
    cfg = dict(DEFAULTS)
    op = OptionParser()
    op.add_option("-c", "--conffile", action="store")
    op.add_option("-v", "--verbose", action="store_true")
#    op.add_option("-k", "--kill", action="store_true")
    op.add_option("-s", "--single", action="store_true")
    op.add_option("-n", "--version", action="store_true")
    op.add_option("-y", "--ppid", action="store", type='int')
#    op.add_option("-i", "--identity", action="store")
    op.add_option("-p", "--command_port", action="store", type='int')
    (options, args) = op.parse_args(args[1:])
    agent = PortAgent(options)
    agent.start()
    return 0


