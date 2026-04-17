#!/usr/bin/env python2
# -*- coding: utf-8 -*-


class UIContext:
    MIN_ROWS = 17
    MIN_COLS = 60

    def __init__(self):
        self.rows = 0
        self.cols = 0
        self.half_cols = 0

    def update_dimensions(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.half_cols = int(cols / 2)

    def is_too_small(self):
        return self.rows < self.MIN_ROWS or self.cols < self.MIN_COLS


class AppState:
    def __init__(self):
        self.user_idx = 0
        self.keyword = ''
        self.login_method_idx = 1
        self.active_group_name = ''


class UserState:
    def __init__(self, app):
        self.app = app
        self.users = ['irteam', 'irteamsu']
        self.login_methods = ['rlogin', 'ssh']

    def change_user(self):
        self.app.user_idx = (self.app.user_idx + 1) % 2

    def change_login_method(self):
        self.app.login_method_idx = (self.app.login_method_idx + 1) % 2

    def get_user(self):
        return self.users[self.app.user_idx]

    def get_login_method(self):
        return self.login_methods[self.app.login_method_idx]
