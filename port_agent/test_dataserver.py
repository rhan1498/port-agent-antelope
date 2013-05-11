#!/usr/bin/env python

import unittest

from mock import Mock, MagicMock

from gevent import sleep, spawn, wait
from gevent.socket import create_connection
from gevent.queue import Queue

from dataserver import DataServer
from packet import ReceivedPacket

DATA_PORT = 54321

class Test_DataServer(unittest.TestCase):
    def setUp(self):
        self.cfg = Mock()
        self.cfg.data_port = DATA_PORT
        self.q = Queue()
        self.orbpktsrc = MagicMock()
        self.orbpktsrc.subscription.return_value.__enter__.return_value = self.q
        self.ds = DataServer(self.cfg, self.orbpktsrc)

    def test_DataServer(self):
        self.cfg.heartbeat_interval = 10
        [self.q.put(('', float(n))) for n in xrange(15)]
        received = []
        def rx():
            try:
                self.ds.start()
                sock = create_connection(('127.0.0.1', DATA_PORT), timeout=2)
                while True:
                    received.append(sock.recv(0x10))
            finally:
                self.ds.stop()
        rxg = spawn(rx)
        sleep(1)
        rxg.kill()
        self.assertEquals(len(received), 15)

    def test_DataServer_heartbeat(self):
        self.cfg.heartbeat_interval = 1
        received = []
        def rx():
            try:
                self.ds.start()
                sock = create_connection(('127.0.0.1', DATA_PORT), timeout=2)
                while True:
                    received.append(sock.recv(0x10))
            finally:
                self.ds.stop()
        rxg = spawn(rx)
        sleep(1.5)
        rxg.kill()
        self.assertEquals(len(received), 1)

if __name__ == '__main__':
    unittest.main()

