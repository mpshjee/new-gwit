#!/usr/bin/env python2
# -*- coding: utf-8 -*-


class Context:
    MIN_ROWS = 17
    MIN_COLS = 60

    def __init__(self):
        self.user_idx = 0
        self.keyword = ''
        self.rows = 0
        self.cols = 0
        self.half_cols = 0
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
