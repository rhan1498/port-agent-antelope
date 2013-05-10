#!/usr/bin/env python
from twisted.internet import reactor


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


class PortAgentConfig(object):
    cmds = {
        'heartbeat_interval': (int, None),
        'command_port': (int, None),
        'data_port': (int, None),
        'pid_dir': (str, "/tmp"),
        'log_level': (str, 'warn'),
    }

    def __init__(self, options, cmdproc):
        for name, (converter, default) in self.cmds.iteritems():
            # Initialize attr with default val
            setattr(self, name, default)
            # Create command to set attr
            cmdproc.setCmd(name, converter, lambda val: setattr(self, name, val))

        # update from config file
        if hasattr(options, 'conffile'):
            self.readConfig(options.conffile)
        # update from command line

    def readConfig(self, conffile):
        with open(conffile, 'rU') as file:
            for line in file:
                self.cmdproc.process(line)


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


from orbreapthr import OrbreapThr


class OrbPktSrc(OrbReapThr):
    def __init__(self, srcname, select, reject):
        self.source = OrbreapThr(srcname, select, reject, timeout=1)
        self.source.orbname = srcname

    def get(self):
        d = self.source.get()
        d.addCallbacks(self.on_get, errback=self.on_get_error)
        return d

    def on_get_error(self, failure):
        failure.trap(Timeout, NoData)
        return self.get(source)

    def on_get(self, pkt):
        # unstuff
        # do something; send to connected port agent clients
        r = self.update(pfdict)
        self.get()
        return r




from twisted.internet import reactor, protocol
from twisted.protocols.basic import LineReceiver

class CmdProtocol(LineReceiver):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        # log something
        pass

    def connectionLost(self, reason):
        # log something
        pass

    def lineReceived(self, line):
        # handle command
        pass

class CmdFactory(protocol.Factory):
    def __init__(self):
        pass

    def buildProtocol(self, addr):
        return CmdProtocol(self)

# reactor.listenTCP(config.cmd_port, CmdFactory())


class DataProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        self.factory.clients.add(self)

    def connectionLost(self, reason):
        self.factory.clients.remove(self)

    def sendPkt(self, pkt):
        self.transport.write(pkt)

class DataFactory(protocol.Factory):
    def __init__(self):
        self.clients = set()

    def buildProtocol(self, addr):
        return DataProtocol(self)

    def sendPkt(self, pkt):
        for c in self.clients:
            c.sendPkt(pkt)


# datafactory = DataFactory()
# reactor.listenTCP(config.cmd_port, datafactory)

#!/usr/bin/env python

import sys
from optparse import OptionParser

from port_agent.port_agent import PortAgent

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


