#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import os

from config import server_list_json_file


class ServerManager:
    def __init__(self, app, server_group_manager):
        self.app = app
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

        if self.app.keyword != '':
            keywords = self.app.keyword.split(' ')
            for k in keywords:
                self.filtered_servers = list(filter(lambda s: self._is_matched(s, k), self.filtered_servers))

        if self.app.active_group_name:
            group_hosts = set(self.server_group_manager.get_hosts_in_group(self.app.active_group_name))
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
        if self.app.login_method_idx == 0:
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
