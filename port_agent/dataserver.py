#!/usr/bin/env python

from contextlib import closing

from gevent import spawn, sleep
from gevent.coros import Semaphore
from gevent.server import StreamServer

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

    def handle(self, sock, addr):
        with closing(sock):
            socklock = Semaphore()
            spawn(self.heartbeat_sender, sock, addr, socklock)
            with self.orbpktsrc.subscription() as queue:
                while True:
                    orbpkt, timestamp = queue.get()
                    pkt = makepacket(MSG_TYPE_INSTRUMENT_DATA, timestamp, orbpkt)
                    with socklock:
                        sock.sendall(pkt)

    def heartbeat_sender(self, sock, addr, socklock):
        with closing(sock):
            while True:
                sleep(self.cfg.heartbeat_interval)
                pkt = makepacket(MSG_TYPE_HEARTBEAT, ntp.now(), '')
                with socklock:
                    sock.sendall(pkt)


class CmdServer(StreamServer):
    def __init__(self, cfg, cmdproc):
        self.cfg = cfg
        self.cmdproc = cmdproc
        super(CmdServer, self).__init__(
            listener = ('localhost', cfg.command_port),
            spawn = POOL_SIZE
        )

    def handle(self, sock, addr):
        with closing(sock):
            headerbuf = bytearray(HEADER_SIZE)
            view = memoryview(headerbuf)
            bytesrx = HEADER_SIZE
            while True:
                while bytesrx:
                    bytesrx -= sock.recv_into(view[HEADER_SIZE - bytesrx:], bytesrx)
                pkt = ReceivedPacket(headerbuf)
                datasize = pkt.pktsize - HEADER_SIZE
                bytesrx = datasize
                databuf = bytearray(bytesrx)
                view = memoryview(databuf)
                while bytesrx:
                    bytesrx -= sock.recv_into(view[datasize - bytesrx:], bytesrx)
                pkt.validate(databuf)
                # check msg type
                for cmd in pkt.data.split():
                    self.cmdproc.processCmd(str(cmd))

