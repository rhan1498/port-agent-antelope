#!/usr/bin/env python

from contextlib import closing

from gevent import spawn, sleep
from gevent.coros import Semaphore
from gevent.server import StreamServer

from ooi.logging import log

from packet import makepacket, ReceivedPacket, HEADER_SIZE, MAX_PACKET_SIZE, \
                   MSG_TYPE_INSTRUMENT_DATA, MSG_TYPE_HEARTBEAT
import ntp


POOL_SIZE = 100


class DataServer(StreamServer):
    def __init__(self, cfg, orbpktsrc):
        self.cfg = cfg
        self.orbpktsrc = orbpktsrc
        super(DataServer, self).__init__(
            listener = ('localhost', cfg.data_port),
            spawn = POOL_SIZE
        )

    def start(self, *args, **kwargs):
        log.info("DataServer listening on %s" % self.cfg.data_port)
        super(DataServer, self).start(*args, **kwargs)

    def stop(self, *args, **kwargs):
        log.info("DataServer stopping")
        super(DataServer, self).stop(*args, **kwargs)

    def handle(self, sock, addr):
        try:
            log.info("DataServer accepted connection from %s" % addr)
            with closing(sock):
                socklock = Semaphore()
                spawn(self.heartbeat_sender, sock, addr, socklock)
                with self.orbpktsrc.subscription() as queue:
                    while True:
                        orbpkt, timestamp = queue.get()
                        pkt = makepacket(MSG_TYPE_INSTRUMENT_DATA, timestamp, orbpkt)
                        with socklock:
                            sock.sendall(pkt)
        finally:
            log.info("DataServer connection closed from %s" % addr)

    def heartbeat_sender(self, sock, addr, socklock):
        with closing(sock):
            while True:
                sleep(self.cfg.heartbeat_interval)
                pkt = makepacket(MSG_TYPE_HEARTBEAT, ntp.now(), '')
                with socklock:
                    sock.sendall(pkt)


class SockClosed(Exception): pass

class CmdServer(StreamServer):
    def __init__(self, cfg, cmdproc):
        self.cfg = cfg
        self.cmdproc = cmdproc
        super(CmdServer, self).__init__(
            listener = ('localhost', cfg.command_port),
            spawn = POOL_SIZE
        )

    def start(self, *args, **kwargs):
        log.info("CmdServer listening on %s" % self.cfg.command_port)
        super(CmdServer, self).start(*args, **kwargs)

    def stop(self, *args, **kwargs):
        log.info("CmdServer stopping")
        super(CmdServer, self).stop(*args, **kwargs)

    def handle(self, sock, addr):
        try:
            log.info("CmdServer accepted connection from %s" % addr)
            with closing(sock):
                while True:
                    headerbuf = bytearray(HEADER_SIZE)
                    headerview = memoryview(headerbuf)
                    bytesleft = HEADER_SIZE
                    while bytesleft:
                        bytesrx = sock.recv_into(headerview[HEADER_SIZE - bytesleft:], bytesleft)
                        if bytesrx <= 0:
                            raise SockClosed()
                        bytesleft -= bytesrx
                    pkt = ReceivedPacket(headerbuf)
                    datasize = pkt.pktsize - HEADER_SIZE
                    bytesleft = datasize
                    databuf = bytearray(bytesleft)
                    dataview = memoryview(databuf)
                    while bytesleft:
                        bytesrx = sock.recv_into(dataview[datasize - bytesleft:], bytesleft)
                        if bytesrx <= 0:
                            raise SockClosed()
                        bytesleft -= bytesrx
                    pkt.validate(databuf)
                    # check msg type
                    self.cmdproc.processCmds(str(databuf), sock)
        except SockClosed:
            pass
        finally:
            log.info("CmdServer connection closed from %s" % addr)

