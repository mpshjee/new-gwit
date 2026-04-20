#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import pytest
from data.server_group_manager import ServerGroupManager


class TestLoad:
    def test_no_file_returns_empty(self, isolated_group_store):
        mgr = ServerGroupManager()
        assert mgr.groups == {}

    def test_existing_file_loaded(self, isolated_group_store, tmp_path):
        path = str(tmp_path / 'groups.json')
        with open(path, 'w') as f:
            json.dump({'g1': ['h1', 'h2']}, f)
        mgr = ServerGroupManager()
        assert mgr.groups == {'g1': ['h1', 'h2']}


class TestGroupCRUD:
    def test_create_group(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.create_group('alpha')
        assert 'alpha' in mgr.groups
        assert mgr.groups['alpha'] == []

    def test_create_group_idempotent_keeps_members(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.create_group('alpha')
        mgr.add_to_group('h1', 'alpha')
        mgr.create_group('alpha')
        assert mgr.groups['alpha'] == ['h1']

    def test_delete_group(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.create_group('alpha')
        mgr.delete_group('alpha')
        assert 'alpha' not in mgr.groups

    def test_delete_nonexistent_no_error(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.delete_group('nonexistent')

    def test_get_group_names_sorted(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.create_group('z-group')
        mgr.create_group('a-group')
        assert mgr.get_group_names() == ['a-group', 'z-group']


class TestMembership:
    def test_add_to_group(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_to_group('h1', 'alpha')
        assert mgr.is_in_group('h1', 'alpha') is True

    def test_add_to_group_no_duplicate(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_to_group('h1', 'alpha')
        mgr.add_to_group('h1', 'alpha')
        assert mgr.groups['alpha'].count('h1') == 1

    def test_add_hosts_deduplicates(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_hosts_to_group(['h1', 'h2', 'h1'], 'alpha')
        assert mgr.groups['alpha'].count('h1') == 1
        assert 'h2' in mgr.groups['alpha']

    def test_remove_from_group(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_to_group('h1', 'alpha')
        mgr.remove_from_group('h1', 'alpha')
        assert mgr.is_in_group('h1', 'alpha') is False

    def test_remove_hosts_from_group(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_hosts_to_group(['h1', 'h2', 'h3'], 'alpha')
        mgr.remove_hosts_from_group(['h1', 'h3'], 'alpha')
        assert mgr.groups['alpha'] == ['h2']

    def test_get_groups_of_host_sorted(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_to_group('h1', 'z-group')
        mgr.add_to_group('h1', 'a-group')
        assert mgr.get_groups_of_host('h1') == ['a-group', 'z-group']

    def test_get_non_member_hosts(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_to_group('h1', 'alpha')
        servers = [{'host': 'h1'}, {'host': 'h2'}, {'host': 'h3'}]
        result = mgr.get_non_member_hosts('alpha', servers)
        assert [s['host'] for s in result] == ['h2', 'h3']

    def test_get_member_servers(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_hosts_to_group(['h1', 'h3'], 'alpha')
        servers = [{'host': 'h1'}, {'host': 'h2'}, {'host': 'h3'}]
        result = mgr.get_member_servers('alpha', servers)
        assert [s['host'] for s in result] == ['h1', 'h3']


class TestPersistence:
    def test_save_and_reload(self, isolated_group_store):
        mgr = ServerGroupManager()
        mgr.add_to_group('h1', 'alpha')
        mgr.save()
        mgr2 = ServerGroupManager()
        assert mgr2.is_in_group('h1', 'alpha') is True
        assert mgr2.get_group_names() == ['alpha']
