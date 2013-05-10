#!/usr/bin/env python

from functools import partial

class Config(object):
    cmds = {
        'heartbeat_interval': (int, None),
        'command_port': (int, None),
        'data_port': (int, None),
        'pid_dir': (str, "/tmp"),
        'log_level': (str, 'warn'),
    }

    def __init__(self, options, cmdproc):
        for name, (converter, default) in self.cmds.iteritems():
            self.cmdproc = cmdproc
            # Initialize attr with default val
            setattr(self, name, default)
            # Create command to set attr
            setval = partial(setattr, self, name)
            cmdproc.setCmd(name, converter, setval)

        # update from config file
        if hasattr(options, 'conffile'):
            self.readConfig(options.conffile)
        # update from command line

    def readConfig(self, conffile):
        with open(conffile, 'rU') as file:
            for line in file:
                self.cmdproc.processCmd(line)

    def isConfigured(self):
        return None not in (self.heartbeat_interval, self.command_port,
                            self.data_port)

