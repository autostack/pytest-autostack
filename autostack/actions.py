#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pytest
import ansible
import ansible.runner
import ansible.constants as C
import ansible.inventory
import ansible.utils
import ansible.errors
import ansible.playbook
import ansible.inventory

from ansible import callbacks

from autostack.errors import AnsibleCompoundException
from autostack.environment import Compound

from pkg_resources import parse_version
from tempfile import NamedTemporaryFile

has_ansible_become = \
    parse_version(ansible.__version__) >= parse_version('1.9.0')


class AnsibleRunnerCallback(callbacks.DefaultRunnerCallbacks):
    '''
    TODO:
    - handle logs
    '''
    def __init__(self, queue):
        self._q = queue

    def on_ok(self, host, res):
        self._q.put({'host': host, 'result': res})
        super(AnsibleRunnerCallback, self).on_ok(host, res)

    def on_async_ok(self, host, res, jid):
        self._q.put({'host': host, 'result': res})
        super(AnsibleRunnerCallback, self).on_async_ok(host, res, jid)


class AnsiblePlaybookRunnerCallback(callbacks.PlaybookRunnerCallbacks):
    def __init__(self, queue, *args, **kwargs):
        super(AnsiblePlaybookRunnerCallback, self).__init__(*args, **kwargs)
        self._q = queue

    def on_ok(self, host, res):
        self._q.put({'host': host, 'result': res})
        super(AnsiblePlaybookRunnerCallback, self).on_ok(host, res)

    def on_async_ok(self, host, res, jid):
        self._q.put({'host': host, 'result': res})
        super(AnsiblePlaybookRunnerCallback, self).on_async_ok(host, res, jid)


class _AnsibleModule(object):
    '''
    Wrapper around ansible.runner.Runner()

    Sample Usage:...
    '''

    def __init__(self, queue, **kwargs):
        self.options = kwargs
        self.queue = queue

        # Module name is used when accessing an instance attribute (e.g.
        # self.ping)
        self.module_name = self.options.get('module_name', None)

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            self.options.update([('module_name', name)])
            return _AnsibleModule(queue=self.queue, **self.options)

    @classmethod
    def _ansible_inventory(cls, nodes):
        '''
        :params nodes: Compound instance slice from environment
        translate inventory to Ansible like file:

        node1.group = clients
        node1.address = 1.1.1.1

        node2.group = servers
        node2.address = 2.2.2.2

        >>> l = [node1, node2]
        >>> _ansible_inventory(l)

        [clients]
        1.1.1.1 connection=smart

        [servers]
        2.2.2.2 connection=smart


        The Ansible like file is relevant only in case of running Playbook.
        Running regular module addhoc is calling "all" hard coded.
        '''
        nodes = nodes if isinstance(nodes, list) else Compound([nodes])

        groups = dict()

        for node in nodes:
            try:
                groups[node.group].append(node.stripe)
            except KeyError:
                groups[node.group] = [node.stripe]

        inventory = ''
        for grp, hosts in groups.iteritems():
            inventory += '[{name}]\n{hosts}\n'.format(
                name=grp, hosts='\n'.join(hosts))

        try:
            temp = NamedTemporaryFile(delete=False)
            temp.write(inventory)
            temp.close()
            return ansible.inventory.Inventory(temp.name)
        except Exception as err:
            raise pytest.UsageError("Failed to initiate inventory!, "
                                    "error: {0}".format(err))

    def setup_context(self, ctx):
        self.setup(ctx.all)
        ctx.set_concrete_os()

    def __call__(self, nodes, *args, **kwargs):
        # Initialize ansible inventory manage
        inventory = self._ansible_inventory(nodes)
        runner_callbacks = AnsibleRunnerCallback(self.queue)

        # Assemble module argument string
        module_args = list()
        if args:
            module_args += list(args)
        module_args = ' '.join(module_args)

        # pop async parameters
        async = kwargs.pop('run_async', False)
        time_limit = kwargs.pop('time_limit', 60)
        forks = kwargs.pop('forks', C.DEFAULT_FORKS)

        # Build module runner object
        kwargs = dict(
            inventory=inventory,
            pattern='all',
            callbacks=runner_callbacks,
            module_name=self.module_name,
            module_args=module_args,
            complex_args=kwargs,
            forks=forks,
            transport=self.options.get('connection'),
            remote_user=self.options.get('user'),
        )

        # Handle >= 1.9.0 options
        if has_ansible_become:
            kwargs.update(dict(
                become=self.options.get('become'),
                become_method=self.options.get('become_method'),
                become_user=self.options.get('become_user'),)
            )
        else:
            kwargs.update(dict(
                sudo=self.options.get('sudo'),
                sudo_user=self.options.get('sudo_user'),)
            )

        runner = ansible.runner.Runner(**kwargs)

        # Run the module
        if async:
            res, poll = runner.run_async(time_limit=time_limit)
            return _ExtendedPoller(res, poll)
        else:
            return _ExtendedPoller(runner.run(), None).poll()

    def run_playbook(self, env, playbook=None):
        '''
        load playbook by priority
        1 - from script: ansible.run_playbook('test.yml')
        2 - from mark: @pytest.mark.ansible(playbook='test.yml')
        3 - from cli: py.test --ansible-playbook test.yml
        '''

        playbook = playbook or self.options.get('playbook')
        inventory = self._ansible_inventory(env)

        # Make sure we aggregate the stats
        stats = callbacks.AggregateStats()
        playbook_cb = callbacks.PlaybookCallbacks(
            verbose=ansible.utils.VERBOSITY)
        runner_cb = AnsiblePlaybookRunnerCallback(
            self.queue, stats, verbose=ansible.utils.VERBOSITY)


        # TODO: add forks=int
        pb = ansible.playbook.PlayBook(
            playbook=playbook,
            remote_user=self.options.get('user'),
            callbacks=playbook_cb,
            runner_callbacks=runner_cb,
            inventory=inventory,
            stats=stats
        )
        return pb.run()


class _ExtendedPoller(object):
    def __init__(self, result, poller):
        self.__res = result
        self.__poll = poller

    def __getattr__(self, name):
        return getattr(self.__poll, name)

    def __expose_failure(self):
        is_failur = all((res.get('failed', False) or res.get('rc', 0) != 0
                         for host, res in self.__res['contacted'].iteritems()))
        if is_failur or self.__res['dark']:
            raise AnsibleCompoundException(
                'Some of the hosts had failed', **self.__res)

        return self.__res['contacted']

    def poll(self):
        if hasattr(self.__poll, 'poll'):
            return self.__poll.poll()
        else:
            return self.__expose_failure()

    def wait(self, seconds, poll_interval):
        self.__res = self.__poll.wait(seconds, poll_interval)
        return self.__expose_failure()


def initialize_ansible(request, queue):

    _request = request
    # Remember the pytest request attr
    kwargs = dict(__request__=request)
    kwargs['queue'] = queue

    # Grab options from command-line
    option_names = ['ansible_playbook',
                    'ansible_connection',
                    'ansible_user',
                    'ansible_sudo',
                    'ansible_sudo_user']

    # Grab ansible-1.9 become options
    if has_ansible_become:
        option_names.extend(['ansible_become',
                             'ansible_become_method',
                             'ansible_become_user'])

    kwargs.update({key[8:]: _request.config.getvalue(key)
                   for key in option_names})

    # Override options from @pytest.mark.ansible
    ansible_args = dict()
    if _request.scope == 'function':
        if hasattr(_request.function, 'ansible'):
            ansible_args = _request.function.ansible.kwargs
    elif _request.scope == 'class':
        if hasattr(_request.cls, 'pytestmark'):
            for mark in _request.cls.pytestmark:
                if mark.name == 'ansible':
                    ansible_args = mark.kwargs

    # Build kwargs to pass along to AnsibleModule
    for key in option_names:
        try:
            short_key = key[8:]
            kwargs[short_key] = ansible_args[short_key]
        except KeyError:
            pass

    if has_ansible_become:
        # normalize ansible.ansible_become options
        kwargs['become'] = kwargs['become'] or \
            kwargs['sudo'] or C.DEFAULT_BECOME
        kwargs['become_user'] = kwargs['become_user'] or \
            kwargs['sudo_user'] or C.DEFAULT_BECOME_USER

    return _AnsibleModule(**kwargs)

