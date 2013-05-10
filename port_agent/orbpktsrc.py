#!/usr/bin/env python
"""
Gevent based orb packet publisher.

Correct use of this module requires the `ANTELOPE_PYTHON_GILRELEASE`
environment variable to be set, to signal the Antelope Python bindings to
release the GIL when entering Antelope C functions. E.g.

    export ANTELOPE_PYTHON_GILRELEASE=1

"""

from contextlib import contextmanager
from cPickle import dumps
import os

from gevent import Greenlet
from gevent.threadpool import ThreadPool, wrap_errors
from gevent.queue import Queue, Empty

from antelope.brttpkt import OrbreapThr, Timeout, NoData
from antelope.Pkt import Packet


class GilReleaseNotSetError(Exception): pass

if 'ANTELOPE_PYTHON_GILRELEASE' not in os.environ:
    raise GilReleaseNotSetError("ANTELOPE_PYTHON_GILRELEASE not in environment")

class OrbPktSrc(Greenlet):
    """Gevent based orb packet publisher.

    Gets packets from an orbreap thread in a non-blocking fashion using the
    gevent threadpool functionality, serializes them using Pickle (maybe
    something else later? Pickle has serious security issues.) and publishes
    to subscribers.
    """

    def __init__(self, srcname, select, reject):
        Greenlet.__init__(self)
        self.srcname = srcname
        self.select = select
        self.reject = reject
        self._queues = set()

    def _run(self):
        threadpool = ThreadPool(maxsize=1)
        args = self.srcname, self.select, self.reject
        with OrbreapThr(*args, timeout=1) as orbreapthr:
            while True:
                try:
                    success, value = threadpool.spawn(
                            wrap_errors, (Exception,), orbreapthr.get, [], {}).get()
                    if not success:
                        raise value
                except (Timeout, NoData):
                    print "Timeout"
                    pass
                else:
                    if value is None:
                        raise Exception('Nothing to publish')
                    self._publish(value)

    def _publish(self, r):
        pktid, srcname, timestamp, raw_packet = r
        packet = Packet(srcname, timestamp, raw_packet)
        buf = dumps(packet)
        for queue in self._queues:
            queue.put(buf)

    @contextmanager
    def subscription(self):
        queue = Queue()
        self._queues.add(queue)
        yield queue

        # Stop publishing
        del self._queues[queue]

        # Flush queue; is this really necessary?
        try:
            while True:
                queue.get(block=False)
        except Empty:
            pass

    def unsubscribe(self, queue):
        # Could we use some sort of context manager to guarantee that queues
        # are always unsubscribed and never left dangling? Without a max size,
        # a dangling queue would eventually exhaust the heap.

