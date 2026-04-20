#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import pytest
from mock import Mock
from data.server_manager import ServerManager


def _server(host, description='', tags=None):
    return {'host': host, 'description': description, 'tags': tags or []}


def _make_mgr(monkeypatch, tmp_path, servers=None):
    import data.server_manager as sm
    monkeypatch.setattr(sm, 'server_list_json_file', str(tmp_path / 'servers.json'))
    if servers is not None:
        with open(str(tmp_path / 'servers.json'), 'w') as f:
            json.dump(servers, f)
    app = Mock()
    app.keyword = ''
    app.active_group_name = ''
    app.login_method_idx = 1
    sgm = Mock()
    sgm.get_hosts_in_group = Mock(return_value=[])
    return ServerManager(app, sgm)


class TestIsMatched:
    def test_match_host_partial(self, monkeypatch, tmp_path):
        mgr = _make_mgr(monkeypatch, tmp_path)
        assert mgr._is_matched(_server('web-server-01'), 'web') is True

    def test_match_host_case_insensitive(self, monkeypatch, tmp_path):
        mgr = _make_mgr(monkeypatch, tmp_path)
        assert mgr._is_matched(_server('WEB-SERVER'), 'web') is True

    def test_match_description(self, monkeypatch, tmp_path):
        mgr = _make_mgr(monkeypatch, tmp_path)
        assert mgr._is_matched(_server('h1', description='production server'), 'prod') is True

    def test_match_tag(self, monkeypatch, tmp_path):
        mgr = _make_mgr(monkeypatch, tmp_path)
        assert mgr._is_matched(_server('h1', tags=['mysql', 'backend']), 'mysql') is True

    def test_no_match(self, monkeypatch, tmp_path):
        mgr = _make_mgr(monkeypatch, tmp_path)
        assert mgr._is_matched(_server('h1', description='nothing', tags=['abc']), 'xyz') is False


class TestFilter:
    def test_single_keyword(self, monkeypatch, tmp_path):
        servers = [_server('web01'), _server('db01')]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        mgr.app.keyword = 'web'
        mgr.filter()
        assert [s['host'] for s in mgr.filtered_servers] == ['web01']

    def test_and_condition_space_separated(self, monkeypatch, tmp_path):
        servers = [
            _server('web01', tags=['prod']),
            _server('web02', tags=['dev']),
            _server('db01', tags=['prod']),
        ]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        mgr.app.keyword = 'web prod'
        mgr.filter()
        assert [s['host'] for s in mgr.filtered_servers] == ['web01']

    def test_empty_keyword_returns_all(self, monkeypatch, tmp_path):
        servers = [_server('h1'), _server('h2')]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        mgr.app.keyword = ''
        mgr.filter()
        assert len(mgr.filtered_servers) == 2

    def test_filter_by_active_group(self, monkeypatch, tmp_path):
        servers = [_server('h1'), _server('h2'), _server('h3')]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        mgr.app.active_group_name = 'mygroup'
        mgr.server_group_manager.get_hosts_in_group.return_value = ['h1', 'h3']
        mgr.filter()
        assert [s['host'] for s in mgr.filtered_servers] == ['h1', 'h3']


class TestServerCRUD:
    def test_insert_server(self, monkeypatch, tmp_path):
        mgr = _make_mgr(monkeypatch, tmp_path)
        mgr.insert_server(_server('new-host'))
        assert any(s['host'] == 'new-host' for s in mgr.servers)

    def test_insert_duplicate_host_ignored(self, monkeypatch, tmp_path):
        servers = [_server('h1')]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        mgr.insert_server(_server('h1'))
        assert len([s for s in mgr.servers if s['host'] == 'h1']) == 1

    def test_delete_server(self, monkeypatch, tmp_path):
        servers = [_server('h1'), _server('h2')]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        mgr.delete_server('h1')
        assert not any(s['host'] == 'h1' for s in mgr.servers)
        assert any(s['host'] == 'h2' for s in mgr.servers)

    def test_is_duplicated_host_true(self, monkeypatch, tmp_path):
        servers = [_server('h1')]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        assert mgr.is_duplicated_host('h1') is True

    def test_is_duplicated_host_same_original_false(self, monkeypatch, tmp_path):
        servers = [_server('h1')]
        mgr = _make_mgr(monkeypatch, tmp_path, servers)
        assert mgr.is_duplicated_host('h1', original_host='h1') is False

    def test_save_and_reload(self, monkeypatch, tmp_path):
        mgr = _make_mgr(monkeypatch, tmp_path)
        mgr.insert_server(_server('saved-host'))
        mgr.save_to_json()
        mgr2 = _make_mgr(monkeypatch, tmp_path)
        assert any(s['host'] == 'saved-host' for s in mgr2.servers)
