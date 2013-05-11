#!/usr/bin/env Python

from gevent import spawn, sleep
from gevent.coros import Semaphore
from gevent.server import StreamServer

from packet import makepacket
import ntp

# TODO support hearbeat
# Should sending a data packet reset the heartbeat timer?
# need to sync heartbeat & data packet sending

POOL_SIZE = 100

class DataServer(StreamServer):
    def __init__(self, cfg, orbpktsrc):
        self.cfg = cfg
        self.orbpktsrc = orbpktsrc
        super(DataServer, self).__init__(
            listener = ('localhost', cfg.data_port),
            spawn = POOL_SIZE
        )

    def handle(self, sock, addr):
        try:
            socklock = Semaphore()
            spawn(self.heartbeat_sender, sock, addr, socklock)
            with self.orbpktsrc.subscription() as queue:
                while True:
                    orbpkt, timestamp = queue.get()
                    pkt = makepacket(1, timestamp, orbpkt)
                    with socklock:
                        sock.sendall(pkt)
        finally:
            sock.close()

    def heartbeat_sender(self, sock, addr, socklock):
        try:
            while True:
                sleep(self.cfg.heartbeat_interval)
                pkt = makepacket(7, ntp.now(), '')
                with socklock:
                    sock.sendall(pkt)
        finally:
            sock.close()

class CmdServer(StreamServer):
    def __init__(self, cfg, cmdproc):
        self.cfg = cfg
        self.cmdproc = cmdproc
        super(CmdServer, self).__init__(
            listener = ('localhost', cfg.command_port),
            spawn = POOL_SIZE
        )

    def handle(self, sock, addr):
        try:
            while True:
                buf = bytearray()
                while len(buf) < 16:
                    sock.recv_into(buf, 16 - len(buf))
                pkt = ReceivedPacket(buf)
                while len(buf) < pkt.pktsize:
                    sock.recv_into(buf, pkt.pktsize - len(buf))
                pkt.validate()
                for cmd in pkt.data.split():
                    self.cmdproc.processCmd(cmd)
        finally:
            sock.close()
