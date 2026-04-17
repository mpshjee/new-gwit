#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import logging
import os

from config import server_list_json_file, server_groups_json_file

logger = logging.getLogger('gwkit')


class Context:
    MIN_ROWS = 17
    MIN_COLS = 60

    def __init__(self):
        self.user_idx = 0
        self.keyword = ''
        self.rows = 0
        self.cols = 0
        self.half_cols = 0
        self.top_help_rows = 10
        self.group_context_rows = 3
        self.top_win_rows = 3
        self.login_method_idx = 1
        self.active_group_name = ''

    def update_dimensions(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.half_cols = int(cols / 2)

    def is_too_small(self):
        return self.rows < self.MIN_ROWS or self.cols < self.MIN_COLS


class UserState:
    def __init__(self, context):
        self.context = context
        self.users = ['irteam', 'irteamsu']
        self.login_methods = ['rlogin', 'ssh']

    def change_user(self):
        self.context.user_idx = (self.context.user_idx + 1) % 2

    def change_login_method(self):
        self.context.login_method_idx = (self.context.login_method_idx + 1) % 2

    def get_user(self):
        return self.users[self.context.user_idx]

    def get_login_method(self):
        return self.login_methods[self.context.login_method_idx]


class ServerGroupManager:
    def __init__(self):
        self.groups = {}  # {group_name: [host, ...]}
        self.load()

    def load(self):
        if os.path.exists(server_groups_json_file):
            with open(server_groups_json_file, 'r') as f:
                self.groups = json.load(f)

    def save(self):
        with open(server_groups_json_file, 'w') as f:
            json.dump(self.groups, f)

    def get_group_names(self):
        return sorted(self.groups.keys())

    def get_hosts_in_group(self, group_name):
        return self.groups.get(group_name, [])

    def is_in_group(self, host, group_name):
        return host in self.groups.get(group_name, [])

    def get_groups_of_host(self, host):
        result = []
        for name, hosts in self.groups.items():
            if host in hosts:
                result.append(name)
        return sorted(result)

    def create_group(self, group_name):
        if group_name not in self.groups:
            self.groups[group_name] = []

    def delete_group(self, group_name):
        if group_name in self.groups:
            del self.groups[group_name]

    def add_to_group(self, host, group_name):
        if group_name not in self.groups:
            self.groups[group_name] = []
        if host not in self.groups[group_name]:
            self.groups[group_name].append(host)

    def remove_from_group(self, host, group_name):
        if group_name in self.groups and host in self.groups[group_name]:
            self.groups[group_name].remove(host)

    def get_non_member_hosts(self, group_name, all_servers):
        members = set(self.get_hosts_in_group(group_name))
        return [s for s in all_servers if s['host'] not in members]


class ServerManager:
    def __init__(self, context, server_group_manager):
        self.context = context
        self.server_group_manager = server_group_manager
        self.servers = []
        self.filtered_servers = []
        self.selected_server_idx = -1
        self.top = 0
        self.bottom = 0
        self.max_host = 30
        self.max_tags = 30
        self.padding = 4
        self.list_height = 0
        self.load_servers()

    def load_servers(self):
        if os.path.exists(server_list_json_file):
            with open(server_list_json_file, 'r') as f:
                self.servers = sorted(json.load(f), key=lambda s: s['host'])
                self.refresh_max()

    def refresh_max(self):
        if len(self.servers) > 0:
            self.max_host = max(map(lambda s: len(s['host']), self.servers))
            self.max_tags = max(map(lambda s: len(', '.join(s['tags'])), self.servers))
        else:
            self.servers = []
            self.max_host = 30
            self.max_tags = 30

    def _is_matched(self, server, keyword):
        upper_keyword = keyword.upper()

        if upper_keyword in server['host'].upper():
            return True

        if upper_keyword in server['description'].upper():
            return True

        for tag in map(lambda t: t.upper(), server['tags']):
            if upper_keyword in tag:
                return True

        return False

    def filter(self, selected_server_idx=None):
        self.filtered_servers = self.servers
        self.top = 0
        self.bottom = self.list_height - self.padding if self.list_height > 0 else 0

        if self.context.keyword != '':
            keywords = self.context.keyword.split(' ')
            for k in keywords:
                self.filtered_servers = list(filter(lambda s: self._is_matched(s, k), self.filtered_servers))

        if self.context.active_group_name:
            group_hosts = set(self.server_group_manager.get_hosts_in_group(self.context.active_group_name))
            self.filtered_servers = [s for s in self.filtered_servers if s['host'] in group_hosts]

        if selected_server_idx is None or selected_server_idx > len(self.filtered_servers) - 1:
            self.selected_server_idx = -1
        else:
            self.selected_server_idx = selected_server_idx

    def select_up(self, delta):
        self.selected_server_idx -= delta
        if self.selected_server_idx < 0:
            self.selected_server_idx = 0

        if self.selected_server_idx < self.top:
            scroll = self.top - self.selected_server_idx
            self.top -= scroll
            self.bottom -= scroll

    def select_down(self, delta):
        self.selected_server_idx += delta
        if self.selected_server_idx > len(self.filtered_servers) - 1:
            self.selected_server_idx = len(self.filtered_servers) - 1

        if self.selected_server_idx > self.bottom:
            scroll = self.selected_server_idx - self.bottom
            self.top += scroll
            self.bottom += scroll

    def connect(self, user):
        if self.selected_server_idx < 0:
            return

        host = self.filtered_servers[self.selected_server_idx]['host']
        if self.context.login_method_idx == 0:
            ret = os.system('rlogin -l {0} {1}'.format(user, host))
            if ret != 0:
                os.system('ssh {0}@{1}'.format(user, host))
        else:
            os.system('ssh {0}@{1}'.format(user, host))

    def save_to_json(self):
        with open(server_list_json_file, 'w') as f:
            json.dump(self.servers, f)

    def insert_server(self, new_server):
        for s in self.servers:
            if s['host'] == new_server['host']:
                return

        self.servers.insert(0, new_server)
        self.filter()

    def delete_current_server(self):
        if self.selected_server_idx < 0:
            return

        deleted = self.filtered_servers.pop(self.selected_server_idx)
        self.servers = list(filter(lambda s: s['host'] != deleted['host'], self.servers))
        self.filter(self.selected_server_idx)

    def get_current_server(self):
        if self.selected_server_idx < 0:
            return None
        else:
            return self.filtered_servers[self.selected_server_idx]

    def is_duplicated_host(self, host, original_host=None):
        if original_host is not None and original_host == host:
            return False

        for s in self.servers:
            if s['host'] == host:
                return True

        return False
