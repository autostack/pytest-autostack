#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import threading
import time


__author__ = 'Avi Tal <avi3tal@gmail.com>'
__date__ = 'Sep 9, 2015'


class Dispatcher(threading.Thread):
    def __init__(self, queue, ctx):
        super(Dispatcher, self).__init__()
        self._q = queue
        self.inventory = ctx
        self.active = True

    def _dispatch(self, host, result):
        nodes = self.inventory.all.filter(address=host)[0]
        try:
            getattr(nodes, '_load_' + result['invocation']['module_name'])(result)
        except AttributeError:
            pass

    def run(self):
        while self.active:
            msg = self._q.get(timeout=60)
            if msg is None:
                time.sleep(5)
                continue
            if msg == 'goodbye':
                self.close()
            else:
                # TODO: handle eval exception
                if isinstance(msg, dict):
                    self._dispatch(**msg)

    def close(self):
        self.active = False
