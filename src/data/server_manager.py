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
        self.load_servers()

    def load_servers(self):
        if os.path.exists(server_list_json_file):
            with open(server_list_json_file, 'r') as f:
                self.servers = sorted(json.load(f), key=lambda s: s['host'])

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

    def filter(self):
        self.filtered_servers = self.servers

        if self.app.keyword != '':
            keywords = self.app.keyword.split(' ')
            for k in keywords:
                self.filtered_servers = list(filter(lambda s: self._is_matched(s, k), self.filtered_servers))

        if self.app.active_group_name:
            group_hosts = set(self.server_group_manager.get_hosts_in_group(self.app.active_group_name))
            self.filtered_servers = [s for s in self.filtered_servers if s['host'] in group_hosts]

    def connect(self, host, user):
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

    def delete_server(self, host):
        self.servers = [s for s in self.servers if s['host'] != host]

    def is_duplicated_host(self, host, original_host=None):
        if original_host is not None and original_host == host:
            return False

        for s in self.servers:
            if s['host'] == host:
                return True

        return False
