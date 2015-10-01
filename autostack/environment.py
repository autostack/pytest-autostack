#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import yaml
import pytest

from autostack.nodes import NodeTemplate
import grp


class Compound(list):
    '''
    '''
    def __call__(self, *args, **kwargs):
        return Compound([child(*args, **kwargs)
                         for child in super(Compound, self).__iter__()])

    def __getattr__(self, item):
        return Compound([getattr(child, item)
                         for child in super(Compound, self).__iter__()])

    def __delattr__(self, item):
        [delattr(child, item) for child in super(Compound, self).__iter__()]

    def __setattr__(self, item, value):
        [setattr(child, item, value)
         for child in super(Compound, self).__iter__()]

    def __getslice__(self, i, j):
        slice_iter = super(Compound, self).__getslice__(i, j)
        return Compound(slice_iter)

    def __add__(self, y):
        iterable = super(Compound, self).__add__(y)
        return Compound(iterable)

    def __sub__(self, other):
        iterable = [item for item in self if item not in other]
        return Compound(iterable)

    def _filter(self, nodes, key, value):
        sub = []
        for child in nodes:
            try:
                if getattr(child, key) == value:
                    sub.append(child)
            except AttributeError:
                continue
        return Compound(sub)

    def filter(self, **kwargs):
        '''Filter, support only AND mode'''
        nodes = self
        for k, v in kwargs.iteritems():
            nodes = self._filter(nodes, k, v)
        return nodes


class Context(dict):
    @property
    def all(self):
        all_set = set()
        for _, hosts in self.iteritems():
            all_set |= set(hosts)
        return Compound(all_set)

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            return super(Context, self).__getattribute__(item)

    def __setitem__(self, key, value):
        if not isinstance(value, Context):
            value = Compound(value)
        super(Context, self).__setitem__(key, value)

    def set_concrete_os(self):
        for k, v in self.iteritems():
            try:
                self.update([(k, v.get_concrete_class())])
            except AttributeError:
                # ignore non NodeTemplate objects
                pass
ctx = Context()


def initialize_context(request, name=None, clear=False):
    global ctx

    with open(request.config.getvalue('inventory'), 'r') as f:
        data = yaml.load(f)

    if name is None:
        # in case of None, choose to use the "default" key from
        # inventory file
        try:
            name = data['default']
        except KeyError:
            raise pytest.UsageError('Failed to locate DEFAULT host group')

    if clear:
        # make sure to create new context
        try:
            del ctx[name]
        except KeyError:
            pass

    try:
        # only verify that name exists in ctx
        ctx[name]
    except KeyError:
        try:
            _ctx = Context()
            for grp, hosts in data[name].iteritems():
                _ctx[grp] = [NodeTemplate(group=grp, **kw) for kw in hosts]

            print(_ctx)
            ctx[name] = _ctx

        except KeyError:
            raise pytest.UsageError('Unkown {} host group! Could not find in inventory file')

    return ctx[name]
