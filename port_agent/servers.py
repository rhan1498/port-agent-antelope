#!/usr/bin/env python

from contextlib import closing
import errno

from gevent import spawn, socket, getcurrent, sleep
from gevent.coros import Semaphore
import gevent.server

from ooi.logging import log

from packet import makepacket, ReceivedPacket, HEADER_SIZE, MAX_PACKET_SIZE, \
                   MSG_TYPE_INSTRUMENT_DATA, MSG_TYPE_HEARTBEAT
import ntp


POOL_SIZE = 100

class SockClosed(Exception): pass

class StreamServer(gevent.server.StreamServer):
    def __init__(self, addr, janitor=None):
        self.addr = addr
        self.janitor = janitor
        super(StreamServer, self).__init__(
            listener = addr,
            spawn = POOL_SIZE
        )

    def start(self, *args, **kwargs):
        log.info("%s listening on %s" % (self.__class__, self.addr))
        super(StreamServer, self).start(*args, **kwargs)

    def stop(self, *args, **kwargs):
        super(StreamServer, self).stop(*args, **kwargs)
        log.info("%s stopped" % self.__class__)

    def handle(self, sock, addr):
        socket_error = ''
        try:
            log.info("%s accepted connection from %s" % (self.__class__, addr,))
            thisgreenlet = getcurrent()
            if self.janitor is not None:
                thisgreenlet.link_exception(self.janitor)
            with closing(sock):
                self.work(sock, addr)
        except SockClosed:
            pass
        except socket.error:
            socket_error = e
        except Exception, e:
            log.error("%s connection terminating due to exception %s" %
                                        (self.__class__, addr,), exc_info=True)
            raise
        finally:
            log.info("%s connection closed from %s %s" % (
                            self.__class__, addr, socket_error))

class DataServer(StreamServer):
    def __init__(self, addr, subscription, heartbeat_event, janitor):
        self.subscription = subscription
        self.heartbeat_event = heartbeat_event
        super(DataServer, self).__init__(addr, janitor)

    def work(self, sock, addr):
        socklock = Semaphore()
        heartbeat = spawn(self.heartbeat_sender, sock, addr,
                          socklock, getcurrent())
        heartbeat.link_exception(self.janitor)
        try:
            with self.subscription() as queue:
                while True:
                    orbpkt, timestamp = queue.get()
                    pkt = makepacket(MSG_TYPE_INSTRUMENT_DATA, timestamp, orbpkt)
                    with socklock:
                        sock.sendall(pkt)
        finally:
            try: heartbeat.kill()
            except: pass

    def heartbeat_sender(self, sock, addr, socklock, parent):
        try:
            with closing(sock):
                while True:
                    self.heartbeat_event.wait()
                    pkt = makepacket(MSG_TYPE_HEARTBEAT, ntp.now(), '')
                    with socklock:
                        sock.sendall(pkt)
                    sleep()
        except socket.error, e:
            log.debug('heartbeat socket err: %s' % e)
        except Exception:
            log.error("heartbeat_sender terminating due to exception", exc_info=True)
            raise
        finally:
            try: parent.kill()
            except: pass


class CmdServer(StreamServer):
    def __init__(self, addr, process_cmds, janitor):
        self.process_cmds = process_cmds
        super(CmdServer, self).__init__(addr, janitor)

    def work(self, sock, addr):
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
            self.process_cmds(str(databuf), sock)

