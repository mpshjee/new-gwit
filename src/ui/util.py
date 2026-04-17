#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses


def safe_addstr(window, y, x, text, attr=0):
    try:
        max_y, max_x = window.getmaxyx()
        if y < 0 or y >= max_y or x < 0 or x >= max_x:
            return
        available = max_x - x - 1
        if available <= 0:
            return
        window.addstr(y, x, text[:available], attr)
    except curses.error:
        pass


def show_status_message(context, msg, color_pair=4):
    try:
        win = curses.newwin(1, context.cols, context.rows - 1, 0)
        safe_addstr(win, 0, 0, msg, curses.color_pair(color_pair))
        win.refresh()
    except curses.error:
        pass


def handle_line_edit_key(key, value, cursor_pos):
    if key == curses.KEY_LEFT:
        if cursor_pos > 0:
            return value, cursor_pos - 1, True
    elif key == curses.KEY_RIGHT:
        if cursor_pos < len(value):
            return value, cursor_pos + 1, True
    elif key == curses.KEY_HOME or key == 1:  # Ctrl-A
        return value, 0, True
    elif key == curses.KEY_END or key == 5:  # Ctrl-E
        return value, len(value), True
    elif key == 8 or key == 127 or key == curses.KEY_BACKSPACE:
        if cursor_pos > 0:
            return value[:cursor_pos - 1] + value[cursor_pos:], cursor_pos - 1, True
    elif key == curses.KEY_DC:
        if cursor_pos < len(value):
            return value[:cursor_pos] + value[cursor_pos + 1:], cursor_pos, True
    elif key == 18:  # Ctrl-R
        return '', 0, True
    elif 32 <= key <= 126:
        return value[:cursor_pos] + chr(key) + value[cursor_pos:], cursor_pos + 1, True
    return value, cursor_pos, False


def calc_popup_dims(context, desired_width=100, desired_height=12):
    max_popup_w = context.cols - 4
    max_popup_h = context.rows - context.top_help_rows - context.top_win_rows - 2

    width = min(desired_width, max_popup_w)
    width = max(width, 40)

    height = min(desired_height, max_popup_h)
    height = max(height, 3)

    x = max(0, (context.cols - width) // 2)
    y = context.top_help_rows + context.top_win_rows + min(4, max(0, max_popup_h - height))

    return height, width, y, x
