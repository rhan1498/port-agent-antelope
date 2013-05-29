#!/usr/bin/env python

# TODO Maybe config updates should emit events?
# Maybe commands should emit events too, and config updates just listen to
# those and or chain them somehow? what about gevent's link thing?

from functools import partial
import os.path

from gevent.event import Event

import logging


class Config(object):
    cmds = {
        'heartbeat_interval': (int, None),
        'command_port': (int, None),
        'data_port': (int, None),
        'pid_dir': (str, "/var/ooici/port_agent/pid"),
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
        'data_port',
        'antelope_orb_name',
        'antelope_orb_select',
        'antelope_orb_reject',
    ]

    def setval(self, name, val, *args, **kwargs):
            setattr(self, name, val)

    def __init__(self, options, cmdproc):
        self.configuredevent = Event()
        self.dataserverconfigupdate = Event()
        self.heartbeatactive = Event()
        for name, (converter, default) in self.cmds.iteritems():
            self.cmdproc = cmdproc
            # Initialize attr with default val
            setattr(self, name, default)
            # Create command to set attr
            # cmdserver sends sock after val; will that mess this up?
            setval = partial(self.setval, name)
            cmdproc.setCmd(name, converter, setval)

        # update from config file
        if hasattr(options, 'conffile') and options.conffile is not None:
            self.readConfig(options.conffile)
        # update from command line
        if hasattr(options, 'verbose') and options.verbose is True:
            logging.getLogger().setLevel(logging.DEBUG)
        if hasattr(options, 'command_port') and options.command_port is not None:
            self.command_port = options.command_port

    def readConfig(self, conffile):
        with open(conffile, 'rU') as file:
            for line in file:
                self.cmdproc.processCmd(line)

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
        # TODO: make heartbeat_interval a property?
        if name == 'heartbeat_interval':
            if value > 0:
                self.heartbeatactive.set()
            else:
                self.heartbeatactive.clear()

