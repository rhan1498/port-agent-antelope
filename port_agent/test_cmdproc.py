#!/usr/bin/env python

import unittest

import mock

from cmdproc import CmdProcessor, CmdParseError, ValueConversionError, \
                    CmdUsageError


class Test_CmdProcessor(unittest.TestCase):
    def setUp(self):
        self.cp = CmdProcessor()

    def test_setCmd(self):
        self.cp.setCmd('cmd', None, None)

    def test_parseCmd(self):
        r = self.cp._parseCmd('foo')
        self.assertEquals(r, ('foo', None))

    def test_parseCmd2(self):
        r = self.cp._parseCmd('foo bar')
        self.assertEquals(r, ('foo', 'bar'))

    def test_parseCmd3(self):
        self.assertRaises(CmdParseError, self.cp._parseCmd, 'foo bar baz')

    def test_processCmd(self):
        sentinel = []
        outerval = '123'
        def cb(innerval, *args, **kwargs):
            self.assertEquals(innerval, 123)
            self.assertEquals(args, ('astr', 'bstr'))
            self.assertEquals(kwargs, dict(foo='bar', sna='foo'))
            sentinel.append(0)
        self.cp.setCmd('cmd', int, cb, 'astr', foo='bar')
        self.cp.processCmd('cmd 123', 'bstr', sna='foo')
        self.assertEquals(sentinel, [0])

    def test_processCmd2(self):
        def cb(*args, **kwargs):
            pass
        self.cp.setCmd('cmd', int, cb)
        self.assertRaises(ValueConversionError, self.cp.processCmd, 'cmd hello')

    def test_processCmd3(self):
        def cb(*args, **kwargs):
            pass
        self.cp.setCmd('cmd', None, cb)
        self.assertRaises(CmdUsageError, self.cp.processCmd, 'cmd hello')

if __name__ == '__main__':
    unittest.main()

