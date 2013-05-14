#!/usr/bin/env python

from optparse import OptionParser
import sys

from gevent import wait

from ooi.logging import config, log

from port_agent import PortAgent

def main(args=None):
    if args is None:
        args = sys.argv
    config.add_configuration('logging.yaml')
#    config.add_configuration('logging-local.yaml')
    op = OptionParser()
    op.add_option("-c", "--conffile", action="store")
    op.add_option("-v", "--verbose", action="store_true")
#    op.add_option("-k", "--kill", action="store_true")
    op.add_option("-s", "--single", action="store_true")
    op.add_option("-n", "--version", action="store_true")
    op.add_option("-y", "--ppid", action="store", type='int')
#    op.add_option("-i", "--identity", action="store")
    op.add_option("-p", "--command_port", action="store", type='int')
    (options, args) = op.parse_args(args[1:])
    agent = PortAgent(options)
    log.info("Starting")
    try:
        agent.start()
        print wait()
        return 0
    except:
        log.critical("Exiting due to exception", exc_info=True)

