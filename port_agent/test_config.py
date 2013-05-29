#!/usr/bin/env python

import unittest
from StringIO import StringIO
from contextlib import closing
from tempfile import NamedTemporaryFile

from gevent import spawn, wait, sleep

import mock

from cmdproc import CmdProcessor, CmdParseError, ValueConversionError, \
                    CmdUsageError

from config import Config

class Test_Config(unittest.TestCase):
    def setUp(self):
        self.cp = CmdProcessor()

    def test_Config(self):
        cfg = Config(None, self.cp)
        self.assertEquals(cfg.pid_dir, '/tmp')
        self.assertIs(cfg.heartbeat_interval, None)
        self.cp.processCmd('heartbeat_interval 0')
        self.assertEquals(cfg.heartbeat_interval, 0)

class Test_readConfig(unittest.TestCase):
    def setUp(self):
        self.cp = CmdProcessor()
        self.cfg = Config(None, self.cp)

    def test_readConfig(self):
        with closing(NamedTemporaryFile()) as tmpfile:
            tmpfile.write('heartbeat_interval 123\n')
            tmpfile.flush()
            self.cfg.readConfig(tmpfile.name)
        self.assertEquals(self.cfg.heartbeat_interval, 123)

class Test_events(unittest.TestCase):
    def setUp(self):
        self.cp = CmdProcessor()
        self.cfg = Config(None, self.cp)
        self.called = False

    def test_configuredevent(self):
        self.assertFalse(self.cfg.configuredevent.isSet())
        self.cfg.heartbeat_interval = 1
        self.cfg.data_port = 1
        self.cfg.antelope_orb_name = 1
        self.assertTrue(self.cfg.configuredevent.isSet())

    def test_dataserverconfigupdate(self):
        def handler():
            self.cfg.dataserverconfigupdate.wait()
            self.called = True
        self.assertFalse(self.cfg.dataserverconfigupdate.isSet())
        spawn(handler)
        sleep(0)
        self.cfg.antelope_orb_select = 1
        wait()
        self.assertTrue(self.called)

if __name__ == '__main__':
    unittest.main()

