#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import os

from config import server_groups_json_file


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
