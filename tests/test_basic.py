#!/usr/bin/ctx python
# -*- coding: UTF-8 -*-

import pytest
import time
from pprint import pprint as pp

__author__ = 'Avi Tal <avi3tal@gmail.com>'
__date__ = 'Sep 1, 2015'


def test_time(ctx):
    time.sleep(1)
    print ctx


def test_false(ctx):
    assert False, 'aaaaaaaaaaaaaaaaa'


@pytest.mark.monitor
def test_ctx(ctx, track):
    print
    pp(ctx)
    l1 = len(ctx)
    print 'Adding test group'
    ctx['test'] = []
    print 'ctx.test >>', ctx.test
    print 'type(ctx.test) >>', type(ctx.test)
    assert len(ctx) - 1 == l1, 'Length was not increased'

    print 'Deleting test group'
    del ctx['test']
    l1 = len(ctx)
    pp(ctx)
    assert len(ctx) == l1, 'Length was not increased'

    track.register(ctx.all.address, ['netwok', 'filesystem'])
    time.sleep(2)
#    assert False, 'aaaaaaaaaajasd,amksndlakisdja,msdakmsndakjsd,ajksd,amn'
    track.unregister(ctx.all.address, ['netwok', 'filesystem'])
    time.sleep(2)


def test_all_attr_exists(ctx):
    assert hasattr(ctx, 'all'), 'all attr does not exists'
    assert hasattr(ctx, 'hosts'), 'hosts attr does not exists'
    ctx['test'] = []
    assert hasattr(ctx, 'test'), 'Failed to add new attr'
    del ctx['test']
    assert not hasattr(ctx, 'test'), 'Failed to delete new attr'


def test_slice(ctx):
    print
    pp(ctx.all[:2])
    pp(ctx.hosts[1])
    pp(ctx.all[-1])


def test_ping(ctx, run):
    print
    pp(run.ping(ctx.all))
    pp(run.ping(ctx.all[0]))
    pp(run.ping(ctx.all[:-1]))


def test_hosts_uname(ctx, run):
    print
    future = run.command(ctx.hosts, 'uname -a', run_async=True)
    print 'Future >>> ', future
    pp(future.wait(60, 2))


@pytest.mark.parametrize('playbook', ['/Users/avi/git/pytest-ansible/tests/play1.yml'])
def test_play1(ctx, run, playbook):
    print
    pp(run.run_playbook(ctx.hosts, playbook))


def test_setup_manually(ctx, run):
    print
    run.setup(ctx.hosts)
    pp(ctx)
    pp(ctx.hosts[1].facts)
#    print ctx.hosts.facts.default_ipv4.address
    ctx.set_concrete_os()
    pp(ctx)
    ctx.set_concrete_os()
    run.setup(ctx.hosts)
    pp(ctx)
    print(type(ctx.hosts[1].facts))


def test_setup_context(ctx, run):
    print
    run.setup_context(ctx)
    print(type(ctx.hosts[1].facts))


def test_only_ctx_facts(ctx):
    print
    print(type(ctx.hosts[1].facts))
