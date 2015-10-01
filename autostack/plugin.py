#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import ansible
import os
import pytest
import ansible.constants as C

from autostack.environment import initialize_context
from autostack.actions import (initialize_ansible, has_ansible_become)
#from autostack.redisq import (RedisQueue, ZeroMQueue)
from autostack.redisq import RedisQueue
from autostack.dispatcher import Dispatcher

__author__ = 'Avi Tal <avi3tal@gmail.com>'
__date__ = 'Sep 1, 2015'


queue = None
requires_inventory = False
host_group = None


def pytest_addoption(parser):
    '''Add options to control ansible.'''

    group = parser.getgroup('Autostack')
    group.addoption('--inventory',
                    default=None,
                    action='store',
                    help='Inventory file URI (default: %default)')
    group.addoption('--host-group',
                    default=None,
                    action='store',
                    help='Set default Inventory host group')
    group.addoption('--ansible-playbook',
                    action='store',
                    dest='ansible_playbook',
                    default=None,
                    metavar='ANSIBLE_PLAYBOOK',
                    help='ansible playbook file URI (default: %default)')
    group.addoption('--ansible-connection',
                    action='store',
                    dest='ansible_connection',
                    default=C.DEFAULT_TRANSPORT,
                    help="connection type to use (default: %default)")
    group.addoption('--ansible-user',
                    action='store',
                    dest='ansible_user',
                    default=C.DEFAULT_REMOTE_USER,
                    help='connect as this user (default: %default)')
    group.addoption('--ansible-debug',
                    action='store_true',
                    dest='ansible_debug',
                    default=False,
                    help='enable ansible connection debugging')

    # classic privilege escalation
    group.addoption('--ansible-sudo',
                    action='store_true',
                    dest='ansible_sudo',
                    default=C.DEFAULT_SUDO,
                    help="run operations with sudo [nopasswd] "
                    "(default: %default) (deprecated, use become)")
    group.addoption('--ansible-sudo-user',
                    action='store',
                    dest='ansible_sudo_user',
                    default='root',
                    help="desired sudo user (default: %default) "
                    "(deprecated, use become)")

    if has_ansible_become:
        # consolidated privilege escalation
        group.addoption('--ansible-become',
                        action='store_true',
                        dest='ansible_become',
                        default=C.DEFAULT_BECOME,
                        help="run operations with become, "
                        "nopasswd implied (default: %default)")
        group.addoption('--ansible-become-method',
                        action='store',
                        dest='ansible_become_method',
                        default=C.DEFAULT_BECOME_METHOD,
                        help="privilege escalation method to use "
                        "(default: %%default), valid "
                        "choices: [ %s ]" % (' | '.join(C.BECOME_METHODS)))
        group.addoption('--ansible-become-user',
                        action='store',
                        dest='ansible_become_user',
                        default=C.DEFAULT_BECOME_USER,
                        help='run operations as this user (default: %default)')


def pytest_configure(config):
    '''
    Maybe could be for deployment period
    '''
    if config.getvalue('ansible_debug'):
        ansible.utils.VERBOSITY = 5
    if config.getvalue('host_group'):
        global host_group
        host_group = config.getvalue('host_group')


def _verify_inventory(config):
    # TODO: add yaml validation
    _inventory = config.getvalue('inventory')
    try:
        return os.path.exists(_inventory)
    except:
        return False


def pytest_collection_modifyitems(session, config, items):
    requires_inventory = False
    for item in items:
        try:
            if not requires_inventory:
                if any([fixture == 'ctx' for fixture in item.fixturenames]):
                    requires_inventory = True
        except AttributeError:
            continue

    if requires_inventory:
        errors = []
        if not _verify_inventory(config):
            errors.append("Unable to load an inventory file, "
                          "specify one with the --inventory parameter.")

        if errors:
            raise pytest.UsageError(*errors)


def pytest_report_header(config):
    '''
    Include the version of infrastructure in the report header
    '''
    return 'Infrastructure version ...'


def pytest_keyboard_interrupt(excinfo):
    if queue is not None:
        queue.join()


def pytest_internalerror(excrepr, excinfo):
    if queue is not None:
        queue.join()


@pytest.yield_fixture(scope='function')
def context(request):
    '''
    '''
    global queue
    global host_group
    queue = RedisQueue()

    group_name = host_group
    clear_mode = False
    if request.scope == 'function':
        if hasattr(request.function, 'inventory'):
            group_name = request.function.inventory.kwargs.get('name', host_group)
            clear_mode = request.function.inventory.kwargs.get('clear', False)
    model = initialize_context(request, group_name, clear_mode)

    consumer = Dispatcher(queue, model)
    consumer.daemon = True
    consumer.start()

    run = initialize_ansible(request, queue)
    run.setup_context(model)

    yield model, run
    queue.join()
