#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os

_script_path = os.path.dirname(os.path.realpath(__file__))
project_root = os.path.dirname(_script_path)
kinit_password = os.path.expanduser('~/.kinit_passwd')
server_list_json_file = '{0}/server_list.json'.format(project_root)
server_groups_json_file = '{0}/server_groups.json'.format(project_root)


class ResizeRequested(Exception):
    pass
