#!/usr/bin/env python
# -*- coding: utf-8 -*-
import curses
from ui.util import handle_line_edit_key, calc_popup_dims
from state import UIContext


def _make_ui(rows, cols):
    ctx = UIContext()
    ctx.update_dimensions(rows, cols)
    return ctx


class TestHandleLineEditKey:
    def test_insert_char_at_start(self):
        value, pos, changed = handle_line_edit_key(ord('a'), '', 0)
        assert value == 'a'
        assert pos == 1
        assert changed is True

    def test_insert_char_in_middle(self):
        value, pos, changed = handle_line_edit_key(ord('x'), 'abc', 2)
        assert value == 'abxc'
        assert pos == 3

    def test_backspace_key_8(self):
        value, pos, changed = handle_line_edit_key(8, 'abc', 3)
        assert value == 'ab'
        assert pos == 2
        assert changed is True

    def test_backspace_key_127(self):
        value, pos, changed = handle_line_edit_key(127, 'abc', 1)
        assert value == 'bc'
        assert pos == 0

    def test_backspace_at_start_no_change(self):
        value, pos, changed = handle_line_edit_key(8, 'abc', 0)
        assert value == 'abc'
        assert pos == 0
        assert changed is False

    def test_delete_key(self):
        value, pos, changed = handle_line_edit_key(curses.KEY_DC, 'abc', 1)
        assert value == 'ac'
        assert pos == 1
        assert changed is True

    def test_delete_at_end_no_change(self):
        _, pos, changed = handle_line_edit_key(curses.KEY_DC, 'abc', 3)
        assert changed is False

    def test_left_arrow_moves_cursor(self):
        _, pos, changed = handle_line_edit_key(curses.KEY_LEFT, 'abc', 2)
        assert pos == 1
        assert changed is True

    def test_left_arrow_at_start_no_change(self):
        _, pos, changed = handle_line_edit_key(curses.KEY_LEFT, 'abc', 0)
        assert pos == 0
        assert changed is False

    def test_right_arrow_moves_cursor(self):
        _, pos, changed = handle_line_edit_key(curses.KEY_RIGHT, 'abc', 1)
        assert pos == 2
        assert changed is True

    def test_right_arrow_at_end_no_change(self):
        _, pos, changed = handle_line_edit_key(curses.KEY_RIGHT, 'abc', 3)
        assert pos == 3
        assert changed is False

    def test_home_key(self):
        _, pos, changed = handle_line_edit_key(curses.KEY_HOME, 'abc', 2)
        assert pos == 0
        assert changed is True

    def test_ctrl_a(self):
        _, pos, changed = handle_line_edit_key(1, 'abc', 2)
        assert pos == 0
        assert changed is True

    def test_end_key(self):
        _, pos, changed = handle_line_edit_key(curses.KEY_END, 'abc', 0)
        assert pos == 3
        assert changed is True

    def test_ctrl_e(self):
        _, pos, changed = handle_line_edit_key(5, 'abc', 0)
        assert pos == 3
        assert changed is True

    def test_ctrl_r_clears(self):
        value, pos, changed = handle_line_edit_key(18, 'hello', 3)
        assert value == ''
        assert pos == 0
        assert changed is True

    def test_unknown_key_no_change(self):
        value, pos, changed = handle_line_edit_key(256, 'abc', 1)
        assert value == 'abc'
        assert pos == 1
        assert changed is False

    def test_non_ascii_high_byte_ignored(self):
        _, _, changed = handle_line_edit_key(200, 'abc', 1)
        assert changed is False


class TestCalcPopupDims:
    def test_normal_size_centered(self):
        ui = _make_ui(24, 80)
        h, w, y, x = calc_popup_dims(ui, desired_width=40, desired_height=10)
        assert h == 10
        assert w == 40
        assert y == (24 - 10) // 2
        assert x == (80 - 40) // 2

    def test_desired_width_clamps_to_min_40(self):
        ui = _make_ui(24, 80)
        _, w, _, _ = calc_popup_dims(ui, desired_width=10, desired_height=10)
        assert w == 40

    def test_desired_height_clamps_to_min_3(self):
        ui = _make_ui(24, 80)
        h, _, _, _ = calc_popup_dims(ui, desired_height=1)
        assert h == 3

    def test_width_limited_by_screen(self):
        ui = _make_ui(24, 50)
        _, w, _, _ = calc_popup_dims(ui, desired_width=100)
        assert w == 50 - 4  # ui.cols - 4
