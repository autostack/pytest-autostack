#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import redis
#import zmq
import time
from uuid import uuid4
from autostack.utilities import get_open_port
from autostack.constants import CAHNNEL_ID


__author__ = 'Avi Tal <avi3tal@gmail.com>'
__date__ = 'Sep 6, 2015'


def gen_key(name):
    return 'autostackqueue:{}'.format(name)


class RedisQueue(object):
    """
    Simple Queue with Redis Backend
    https://redis-py.readthedocs.org/en/latest/
    """
    def __init__(self, name=None, **kwargs):
        """
        The default connection parameters are:
            host='localhost', port=6379, db=0
        """
        self.__db = redis.Redis(**kwargs)
        self.__key = name or gen_key(CAHNNEL_ID)

    def __len__(self):
        """Return the approximate size of the queue."""
        return self.__db.llen(self.key)

    @property
    def key(self):
        return self.__key

    def empty(self):
        """Return True if the queue is empty, False otherwise."""
        return self.qsize() == 0

    def clear(self):
        self.__db.delete(self.key)

    def put(self, item):
        """Put item into the queue."""
        self.__db.rpush(self.key, item)

    def get(self, block=True, timeout=None):
        """Remove and return an item from the queue.

        If optional args block is true and timeout is None (the default), block
        if necessary until an item is available."""
        if block:
            if timeout is None:
                timeout = 0
            item = self.__db.blpop(self.key, timeout=timeout)
            if item is not None:
                item = item[1]
        else:
            item = self.__db.lpop(self.key)

        if item is not None:
            if isinstance(item, str) and item != 'goodbye':
                item = eval(item)
        return item

    def join(self):
        self.put('goodbye')


#class ZeroMQueue(object):
#    def __init__(self, name=None, port='5556', host='127.0.0.1'):
#        self.topic = name or str(uuid4())
#        port = port or get_open_port(host)
#
#        subcontext = zmq.Context()
#        self._subscriber = subcontext.socket(zmq.PULL)
#        self._subscriber.bind('tcp://{}:{}'.format(host, port))
#
#        pubcontext = zmq.Context()
#        self._publisher = pubcontext.socket(zmq.PUSH)
#        self._publisher.connect('tcp://{}:{}'.format(host, port))
#
#    def put(self, item):
#        self._publisher.send_json(item)
#        time.sleep(1)
#
#    def get(self, block=True, timeout=None):
#        if block:
#            item = self._subscriber.recv_json()
#        else:
#            try:
#                item = self._subscriber.recv_json(flags=zmq.NOBLOCK)
#            except zmq.Again as e:
#                pass
#        return item
#
#    def join(self):
#        self.put('goodbye')
