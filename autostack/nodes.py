#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from six import with_metaclass
from autostack.utils import RegisterClasses

__author__ = 'Avi Tal <avi3tal@gmail.com>'
__date__ = 'Sep 8, 2015'


class Facts(dict):
    PREF = 'ansible_'

    def __getattr__(self, attr):
        try:
            data = self[attr]
        except KeyError:
            if attr.startswith(self.PREF):
                raise
            attr = '{}{}'.format(self.PREF, attr)
            data = getattr(self, attr)
        if isinstance(data, dict):
            data = Facts(data)
        return data


class _BaseNode(object):
    def __init__(self, address, **kwargs):
        self.address = address
        self.connection = kwargs.get('connection', 'smart')
        self.user = kwargs.get('user', 'root')
        self._facts = None

    def __repr__(self):
        repr_template = ("<{0.__class__.__module__}.{0.__class__.__name__}"
                         " object at {1} | node ip {2}>")
        return repr_template.format(self, hex(id(self)), self.address)

    @property
    def facts(self):
        return self._facts

    def _load_setup(self, data):
        self._facts = Facts(data['ansible_facts'])

    @property
    def stripe(self):
        return '{ip} connection={conn} ansible_ssh_user={user}'.format(
            ip=self.address, conn=self.connection, user=self.user)

    def get_concrete_class(self):
        '''
        An important abstract method that let us handle rerun
        of Context.set_concrete_os() for non NodeTemplate objects.
        '''
        return self


class NodeTemplate(_BaseNode):
    KLASS_REF = {}

    def __init__(self, address, **kwargs):
        super(NodeTemplate, self).__init__(address, **kwargs)

    def get_concrete_class(self):
        '''
        parsing all parent OS classes registered to this class
        and find out it has concrete os child registered unless
        returning the parent class.
        in case no parent OS have a fit, we return NodeTemplate so that
        in the future user will have the ability to rerun get_concrete_class
        and check is_concrete_class again.
        '''
        try:
            klass = NodeTemplate.KLASS_REF[self.facts.os_family.lower()]
            return klass.get_concrete_os(self.facts)(self)
        except KeyError:
            return self

    @classmethod
    def register(cls, klass):
        cls.KLASS_REF[klass.OS_FAMILY.lower()] = klass


class Node(_BaseNode):
    '''
    Interface class for all type of OS Nodes
    '''
    OS_FAMILY = None

    def __init__(self, node_template_inst):
        node = node_template_inst
        super(Node, self).__init__(
            node.address, connection=node.connection, user=node.user)

    @classmethod
    def get_concrete_os(cls, facts):
        if hasattr(cls, 'registry'):
            for _, klass in cls.registry.iteritems():
                try:
                    if klass.is_concrete_class(facts):
                        cls = klass
                        break
                except:
                    raise
        return cls


class RedHat(with_metaclass(RegisterClasses, Node)):
    OS_FAMILY = 'RedHat'
NodeTemplate.register(RedHat)


class CentOS(RedHat):
    @classmethod
    def is_concrete_class(cls, facts):
        return False


class CentOS7(CentOS):
    @classmethod
    def is_concrete_class(cls, facts):
        return facts.distribution == 'CentOS' and \
            int(facts.distribution_major_version) >= 7
