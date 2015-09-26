#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import threading
import time
import ast
import abc

from autostack.constants import ANSIBLE_CAHNNEL_ID


class Dispatcher(threading.Thread):
    def __init__(self, queue, channel):
        super(Dispatcher, self).__init__()
        self.active = True
        self._q = queue

        self._p = queue.pubsub()
        self._p.subscribe(channel)

    def run(self):
        while self.active:
            msg = self._p.get_message()
            if msg is None:
                time.sleep(0.01)
            elif msg['type'] == 'message':
                data = ast.literal_eval(msg['data'])
                self.do(data)

    @abc.abstractmethod
    def do(self, data):
        pass

    def close(self):
        self.active = False
        self._p.close()


class AnsibleDispatcher(Dispatcher):
    def __init__(self, queue, ctx):
        super(AnsibleDispatcher, self).__init__(queue, ANSIBLE_CAHNNEL_ID)
        self.inventory = ctx

    def _dispatch(self, host, result):
        nodes = self.inventory.all.filter(address=host)[0]
        try:
            getattr(nodes, '_load_' + result['invocation']['module_name'])(result)
        except AttributeError:
            pass

    def do(self, data):
        if data.get('type', None) == 'ANSIBLEDONE':
            self.close()
        else:
            self._dispatch(**data)
