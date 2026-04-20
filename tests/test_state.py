#!/usr/bin/env python
# -*- coding: utf-8 -*-
from state import AppState, UserState, UIContext


class TestUIContext:
    def test_initial_dimensions_are_zero(self):
        ctx = UIContext()
        assert ctx.rows == 0
        assert ctx.cols == 0

    def test_update_dimensions(self):
        ctx = UIContext()
        ctx.update_dimensions(30, 80)
        assert ctx.rows == 30
        assert ctx.cols == 80
        assert ctx.half_cols == 40

    def test_half_cols_truncates_odd(self):
        ctx = UIContext()
        ctx.update_dimensions(30, 81)
        assert ctx.half_cols == 40  # int(81/2)

    def test_is_too_small_below_min_rows(self):
        ctx = UIContext()
        ctx.update_dimensions(UIContext.MIN_ROWS - 1, UIContext.MIN_COLS)
        assert ctx.is_too_small() is True

    def test_is_too_small_exact_min(self):
        ctx = UIContext()
        ctx.update_dimensions(UIContext.MIN_ROWS, UIContext.MIN_COLS)
        assert ctx.is_too_small() is False

    def test_is_too_small_below_min_cols(self):
        ctx = UIContext()
        ctx.update_dimensions(UIContext.MIN_ROWS, UIContext.MIN_COLS - 1)
        assert ctx.is_too_small() is True


class TestAppState:
    def test_initial_values(self):
        app = AppState()
        assert app.user_idx == 0
        assert app.login_method_idx == 1
        assert app.keyword == ''
        assert app.active_group_name == ''


class TestUserState:
    def setup_method(self, _):
        self.app = AppState()
        self.us = UserState(self.app)

    def test_get_user_initial(self):
        assert self.us.get_user() == 'irteam'

    def test_change_user_toggles(self):
        self.us.change_user()
        assert self.us.get_user() == 'irteamsu'

    def test_change_user_wraps_around(self):
        self.us.change_user()
        self.us.change_user()
        assert self.us.get_user() == 'irteam'

    def test_get_login_method_initial(self):
        assert self.us.get_login_method() == 'ssh'  # login_method_idx=1

    def test_change_login_method_toggles(self):
        self.us.change_login_method()
        assert self.us.get_login_method() == 'rlogin'

    def test_change_login_method_wraps_around(self):
        self.us.change_login_method()
        self.us.change_login_method()
        assert self.us.get_login_method() == 'ssh'
