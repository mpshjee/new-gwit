#!/usr/bin/env python2
# -*- coding: utf-8 -*-


def save_server_list(servers, path):
    final_result = str(servers).replace("\'", "\"")
    with open(path, 'w') as f:
        f.write(final_result)
