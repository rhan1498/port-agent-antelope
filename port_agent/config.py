#!/usr/bin/env python

# TODO Maybe config updates should emit events?
# Maybe commands should emit events too, and config updates just listen to
# those and or chain them somehow? what about gevent's link thing?

from functools import partial

from gevent.event import Event

class Config(object):
    cmds = {
        'heartbeat_interval': (int, None),
        'command_port': (int, None),
        'data_port': (int, None),
        'pid_dir': (str, "/tmp"),
        'log_level': (str, 'warn'),
        'antelope_orb_name': (str, None),
        'antelope_orb_select': (str, None),
        'antelope_orb_reject': (str, None),
    }

    CONFIG_DEPS = set([
        'heartbeat_interval',
        'data_port',
        'antelope_orb_name',
    ])

    DATASERVER_DEPS = [
        'heartbeat_interval',
        'data_port',
        'antelope_orb_name',
        'antelope_orb_select',
        'antelope_orb_reject',
    ]

    def __init__(self, options, cmdproc):
        self.configuredevent = Event()
        self.dataserverconfigupdate = Event()
        for name, (converter, default) in self.cmds.iteritems():
            self.cmdproc = cmdproc
            # Initialize attr with default val
            setattr(self, name, default)
            # Create command to set attr
            # cmdserver sends sock after val; will that mess this up?
            setval = partial(setattr, self, name)
            cmdproc.setCmd(name, converter, setval)

        # update from config file
        if hasattr(options, 'conffile') and options.conffile is not None:
            self.readConfig(options.conffile)
        # update from command line
        # what can the cmd line configure anyway? log level?

    def readConfig(self, conffile):
        with open(conffile, 'rU') as file:
            for line in file:
                self.cmdproc.processCmd(line)

    def isConfigured(self):
        return None not in (self.heartbeat_interval, self.command_port,
                            self.data_port, self.antelope_orb_name)

    def __setattr__(self, name, value):
        super(Config, self).__setattr__(name, value)
        if not self.configuredevent.isSet():
            configured_attrs = set()
            for attr in self.CONFIG_DEPS:
                if hasattr(self, attr) and getattr(self, attr) is not None:
                    configured_attrs.add(attr)
            if configured_attrs == self.CONFIG_DEPS:
                self.configuredevent.set()
        if name in self.DATASERVER_DEPS:
            self.dataserverconfigupdate.set()
            self.dataserverconfigupdate.clear()

