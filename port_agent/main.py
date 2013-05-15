#!/usr/bin/env python

from functools import partial
from optparse import OptionParser
import sys
import os
import signal

from daemon import DaemonContext

from lockfile import LockFailed
from lockfile.pidlockfile import PIDLockFile

from cmdproc import CmdProcessor, UnknownCmd


BASE_FILENAME = 'port_agent'
DEFAULT_PID_DIR = "/var/ooici/port_agent/pid"

def get_pidfile(options):
    filename = "%s_%s.pid" % (BASE_FILENAME, options.command_port)
    path = os.path.join(options.pid_dir, filename)
    return path


def start_port_agent(options):
    # DO NOT IMPORT THESE BEFORE ENTERING CONTEXT
#    import gevent
    from config import Config
    from port_agent import PortAgent
    from ooi.logging import config, log
    config.add_configuration('logging.yaml')
    log.info("Starting")
    # get a fresh cmdproc
    cmdproc = CmdProcessor()
    cfg = Config(options, cmdproc)
    agent = PortAgent(cfg, cmdproc)
# NOTE Last time I tested these handlers, Python would crash hard if signaled
# while having an active data connection.
#    gevent.signal(signal.SIGTERM, agent.kill)
#    gevent.signal(signal.SIGINT, agent.kill)
    agent.start()
    agent.join()
    if not agent.successful():
        log.critical("EXIT_FAILURE")
        return 1
    return 0

def main(args=None):
    if args is None:
        args = sys.argv
    op = OptionParser()
    op.add_option("-c", "--conffile", action="store",
                    help='Path to port_agent config file')
    op.add_option("-v", "--verbose", action="store_true")
    op.add_option("-k", "--kill", action="store_true",
                    help='Kill a daemon processes associated to a command port')
    op.add_option("-s", "--single", action="store_true",
                    help='Run in single thread mode. Do not detatch')
    op.add_option("-n", "--version", action="store_true")
#    op.add_option("-y", "--ppid", action="store", type='int',
#                    help='Poison pill, if parent process is gone then shutdown')
#    op.add_option("-i", "--identity", action="store",
#                help='identifiction for the port agent process. Ignored in the port agent process')
    op.add_option("-p", "--command_port", action="store", type='int',
                    help='Observatory command port number')
    (options, args) = op.parse_args(args[1:])

    # We can't import the config module until AFTER we enter the daemon
    # context, so we can't use it to get the command_port and pid_dir
    # parameters from the config file, which we need to determine the path to
    # the PID file.
    options.pid_dir = DEFAULT_PID_DIR
    if options.conffile:
        cmdproc = CmdProcessor()
        if not options.command_port:
            cmdproc.setCmd('command_port', int, partial(setattr, options, 'command_port'))
        cmdproc.setCmd('pid_dir', str, partial(setattr, options, 'pid_dir'))
        with open(options.conffile) as f:
            for line in f:
                try: cmdproc.processCmd(line)
                except UnknownCmd: pass
    if not options.command_port:
        print "Must specify command_port on command line or in conffile"
        return 1

    if options.kill:
        with open(get_pidfile(options)) as f:
            pid = int(f.read().strip())
        print "sending SIGINT to pid %d" % pid
        os.kill(pid, signal.SIGTERM)
        return 0

    context = DaemonContext(
        pidfile = PIDLockFile(get_pidfile(options)),
        working_directory = os.getcwd(),
    )

    if options.single:
        context.detach_process = False
        context.stdout = sys.stdout
        context.stderr = sys.stderr

    try:
        with context:
            return start_port_agent(options)
    except LockFailed:
        print "Failed to lock PID file %r" % get_pidfile(options)
        return 1

    raise Exception("This should be unreachable")
