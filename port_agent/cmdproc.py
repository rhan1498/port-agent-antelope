#!/usr/bin/env python


class CmdParseError(Exception):
    """Raised when the command string cannot be parsed."""
    pass

class ValueConversionError(Exception):
    """Raised when a value string cannot be converted by the specified
    conversion function."""
    pass

class CmdUsageError(Exception):
    """Raised when an argument is passed to a command which does not accept an
    argument."""
    pass


class CmdProcessor(object):
    def __init__(self):
        self.cmds = {}

    def setCmd(self, name, converter, callback, *args, **kwargs):
        self.cmds[name] = converter, callback, args, kwargs

    def _parseCmd(self, cmdstr):
        val = None
        parts = cmdstr.split()
        try:
            name = parts[0]
        except IndexError:
            raise CmdParseError(cmdstr)
        if len(parts) == 2:
            val = parts[1]
        elif len(parts) > 2:
            raise CmdParseError(cmdstr)
        return name, val

    def _executeCmd(self, name, val, *args, **kwargs):
        converter, callback, cbargs, cbkwargs = self.cmds[name]
        if converter is not None:
            try:
                val = converter(val)
            except Exception, e:
                raise ValueConversionError(val, e)
        elif val is not None:
            raise CmdUsageError(name)
        cbargs = list(cbargs)
        cbargs.extend(args)
        kwargs.update(cbkwargs)
        callback(val, *cbargs, **kwargs)

    def processCmd(self, cmdstr, *args, **kwargs):
        name, val = self._parseCmd(cmdstr)
        self._executeCmd(name, val, *args, **kwargs)

    def processCmds(self, cmdsstr, *args, **kwargs):
        for cmdstr in cmdsstr.strip().split('\n'):
            self.processCmd(cmdstr, *args, **kwargs)

