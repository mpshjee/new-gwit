#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import logging
import os
import re

from core import ResizeRequested

logger = logging.getLogger('gwkit')


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


class HelpWindow:
    def __init__(self, context):
        self.context = context
        self.window = curses.newwin(context.top_help_rows, context.cols, 0, 0)
        self.window.scrollok(True)
        self.refresh()

    def refresh(self):
        self.window.clear()
        self.window.border(0)
        safe_addstr(self.window, 0, 5, 'Help')
        mode = self.context.view_mode
        if mode == 'group_list':
            self._render_group_list()
        elif mode == 'group_detail':
            self._render_group_detail()
        else:
            self._render_all()
        self.window.refresh()

    def _render_all(self):
        safe_addstr(self.window, 1, 2, '[/]: change user to rlogin, [,]: change rlogin/ssh')
        safe_addstr(self.window, 2, 2, '[ctrl-n]: register new server     [ctrl-d]: delete server')
        safe_addstr(self.window, 3, 2, '[ctrl-e]: modify server           [ctrl-c]: quit or close popup window')
        safe_addstr(self.window, 4, 2, '[ctrl-r]: reset popup input')
        safe_addstr(self.window, 5, 2, '[:]: command mode (e.g., :groups, :all, :fav <name>, :quit)')
        safe_addstr(self.window, 6, 2, '- registered server will be saved when terminated. (server_list.json)')
        safe_addstr(self.window, 7, 2, '- make "~/.kinit_passwd" to execute kinit automatically.')
        safe_addstr(self.window, 8, 2, '- enter a keyword to filter the list.')

    def _render_group_list(self):
        self._render_all()

    def _render_group_detail(self):
        self._render_all()


class UserWindow:
    def __init__(self, context, user_state):
        self.context = context
        self.user_state = user_state
        self.window = curses.newwin(self.context.top_win_rows, self.context.half_cols, self.context.top_help_rows, 0)
        self.window.scrollok(True)
        self.refresh_user_border()

    def change_user(self):
        self.user_state.change_user()
        self.window.clear()
        self.refresh_user_border()

    def change_login_method(self):
        self.user_state.change_login_method()
        self.window.clear()
        self.refresh_user_border()

    def refresh_user_border(self):
        self.window.border(0)
        safe_addstr(self.window, 1, 2, "user : " + self.user_state.get_user() + ", [ " + self.user_state.get_login_method() + " ]")
        self.window.refresh()


class KeywordWindow:
    def __init__(self, context):
        self.context = context
        self.window = curses.newwin(self.context.top_win_rows, self.context.half_cols, self.context.top_help_rows, self.context.half_cols)
        self.window.scrollok(True)
        self.window.keypad(True)
        self.window.border(0)
        self.cursor_pos = len(self.context.keyword)
        self.refresh_display()

    def getch(self):
        return self.window.getch()

    def refresh(self):
        self.window.refresh()

    def refresh_display(self):
        self.window.move(1, 2)
        self.window.clrtoeol()

        prefix = "keyword : "
        safe_addstr(self.window, 1, 2, prefix, curses.color_pair(0))

        available_width = max(0, self.context.half_cols - 4 - len(prefix))
        display_width = max(available_width, len(self.context.keyword) + 5)

        if len(self.context.keyword) == 0:
            display_text = " " * max(1, display_width)
        else:
            display_text = self.context.keyword + " " * (display_width - len(self.context.keyword))

        start_x = 2 + len(prefix)
        max_x = self.context.half_cols - 2
        for i in range(min(display_width, available_width)):
            if start_x + i >= max_x:
                break

            if i < len(display_text):
                char = display_text[i]
            else:
                char = " "

            if i == self.cursor_pos:
                if char == " ":
                    safe_addstr(self.window, 1, start_x + i, "_", curses.color_pair(2) | curses.A_BOLD)
                else:
                    safe_addstr(self.window, 1, start_x + i, char, curses.color_pair(1) | curses.A_BOLD)
            else:
                safe_addstr(self.window, 1, start_x + i, char, curses.color_pair(0))

        self.window.refresh()

    def process(self, key):
        if key == curses.KEY_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
                self.refresh_display()
        elif key == curses.KEY_RIGHT:
            if self.cursor_pos < len(self.context.keyword):
                self.cursor_pos += 1
                self.refresh_display()
        elif key == curses.KEY_HOME or key == 1:  # Ctrl-A
            self.cursor_pos = 0
            self.refresh_display()
        elif key == curses.KEY_END or key == 5:  # Ctrl-E
            self.cursor_pos = len(self.context.keyword)
            self.refresh_display()
        elif key == 8 or key == 127 or key == curses.KEY_BACKSPACE:
            if self.cursor_pos > 0:
                self.context.keyword = self.context.keyword[:self.cursor_pos-1] + self.context.keyword[self.cursor_pos:]
                self.cursor_pos -= 1
                self.refresh_display()
        elif key == curses.KEY_DC:
            if self.cursor_pos < len(self.context.keyword):
                self.context.keyword = self.context.keyword[:self.cursor_pos] + self.context.keyword[self.cursor_pos+1:]
                self.refresh_display()
        elif key == 18:  # Ctrl-R
            self.context.keyword = ''
            self.cursor_pos = 0
            self.refresh_display()
        elif key >= 32 and key <= 126:
            self.context.keyword = self.context.keyword[:self.cursor_pos] + chr(key) + self.context.keyword[self.cursor_pos:]
            self.cursor_pos += 1
            self.refresh_display()


class ServerListWindow:
    def __init__(self, context, server_manager):
        self.context = context
        self.server_manager = server_manager
        self.window = curses.newwin(self.context.rows - self.context.top_help_rows - self.context.top_win_rows,
                                    self.context.cols,
                                    self.context.top_help_rows + self.context.top_win_rows,
                                    0)
        self.window.scrollok(True)

    def _print_color_text(self, text, index, y, x, width):
        max_y, max_x = self.window.getmaxyx()
        if y < 0 or y >= max_y:
            return

        keywords = list(map(lambda k: k.upper(), self.context.keyword.rstrip().split(' ')))
        for k in keywords:
            pattern = re.compile("(" + k + ")", re.IGNORECASE)
            match = pattern.search(text, 0, len(text) - 1)
            if match is None:
                continue

            for group in match.groups():
                text = pattern.sub(' ' + group + ' ', text)

        color_index = 0
        text_length = 0
        words = text.split(' ')
        for word in words:
            color_index = 0
            if index == self.server_manager.selected_server_idx:
                color_index += 1

            if word.upper() in keywords:
                color_index += 2

            safe_addstr(self.window, y, x + text_length, word, curses.color_pair(color_index))
            text_length += len(word)

        if width > 0 and text_length < width:
            safe_addstr(self.window, y, x + text_length, ''.ljust(width - text_length), curses.color_pair(color_index))

    def refresh(self):
        sm = self.server_manager
        DEFAULT_PAD_LEN = 5
        HOST_X = DEFAULT_PAD_LEN
        TAGS_X = sm.max_host + DEFAULT_PAD_LEN * 2
        DESC_X = sm.max_host + sm.max_tags + DEFAULT_PAD_LEN * 3

        self.window.clear()
        self.window.border(0)
        safe_addstr(self.window, 0, HOST_X, 'Host')
        safe_addstr(self.window, 0, TAGS_X, 'Tags')
        safe_addstr(self.window, 0, DESC_X, 'Description')

        max_y = self.window.getmaxyx()[0]
        for (index, server) in enumerate(sm.filtered_servers):
            if index < sm.top:
                continue

            if index > sm.bottom:
                break

            row_y = index - sm.top + 2
            if row_y >= max_y - 1:
                break

            self._print_color_text(server['host'], index, row_y, HOST_X, sm.max_host + DEFAULT_PAD_LEN)
            self._print_color_text(', '.join(server['tags']), index, row_y, TAGS_X, sm.max_tags + DEFAULT_PAD_LEN)
            self._print_color_text(server['description'], index, row_y, DESC_X, -1)
        self.window.refresh()


class InputLabel:
    def __init__(self, window, padding_left, prefix, value=None):
        self.window = window
        self.prefix = prefix
        self.value = ''
        if value is not None:
            self.value = value
        self.min_x = padding_left + len(self.prefix) + 1
        self.x = self.min_x + len(self.value)
        self.cursor_pos = len(self.value)
        self.y = 0
        self.label_x = 0
        self.is_active = False

    def process_key(self, key):
        if key == curses.KEY_LEFT:
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
                self.refresh_display()
        elif key == curses.KEY_RIGHT:
            if self.cursor_pos < len(self.value):
                self.cursor_pos += 1
                self.refresh_display()
        elif key == curses.KEY_HOME or key == 1:  # Ctrl-A
            self.cursor_pos = 0
            self.refresh_display()
        elif key == curses.KEY_END or key == 5:  # Ctrl-E
            self.cursor_pos = len(self.value)
            self.refresh_display()
        elif key == 8 or key == 127 or key == curses.KEY_BACKSPACE:
            if self.cursor_pos > 0:
                self.value = self.value[:self.cursor_pos-1] + self.value[self.cursor_pos:]
                self.cursor_pos -= 1
                self.refresh_display()
        elif key == curses.KEY_DC:
            if self.cursor_pos < len(self.value):
                self.value = self.value[:self.cursor_pos] + self.value[self.cursor_pos+1:]
                self.refresh_display()
        elif key == 18:  # Ctrl-R
            self.value = ''
            self.cursor_pos = 0
            self.refresh_display()
        elif key >= 32 and key <= 126:
            self.value = self.value[:self.cursor_pos] + chr(key) + self.value[self.cursor_pos:]
            self.cursor_pos += 1
            self.refresh_display()

    def set_active(self, active):
        self.is_active = active
        self.refresh_display()

    def refresh_display(self):
        self.window.move(self.y, self.label_x)
        self.window.clrtoeol()

        safe_addstr(self.window, self.y, self.label_x, self.prefix + " ", curses.color_pair(5))

        max_x = self.window.getmaxyx()[1]
        display_width = max(20, len(self.value) + 5)
        display_text = self.value + " " * (display_width - len(self.value))

        for i in range(display_width):
            if self.min_x + i >= max_x - 1:
                break

            if i < len(display_text):
                char = display_text[i]
            else:
                char = " "

            if self.is_active and i == self.cursor_pos:
                safe_addstr(self.window, self.y, self.min_x + i, char, curses.color_pair(6))
            else:
                safe_addstr(self.window, self.y, self.min_x + i, char, curses.color_pair(7))

    def print_label(self, y, x):
        self.y = y
        self.label_x = x

        safe_addstr(self.window, y, x, self.prefix + " ", curses.color_pair(5))

        max_x = self.window.getmaxyx()[1]
        display_width = max(20, len(self.value) + 5)
        display_text = self.value + " " * (display_width - len(self.value))

        for i in range(display_width):
            if self.min_x + i >= max_x - 1:
                break

            if i < len(display_text):
                char = display_text[i]
            else:
                char = " "

            if self.is_active and i == self.cursor_pos:
                safe_addstr(self.window, y, self.min_x + i, char, curses.color_pair(6))
            else:
                safe_addstr(self.window, y, self.min_x + i, char, curses.color_pair(7))


class LoadTipsServerList:
    def __init__(self, context, sso_id=None, sso_pw=None):
        h, w, y, x = calc_popup_dims(context, desired_width=100, desired_height=12)
        self.context = context
        self.window = curses.newwin(h, w, y, x)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        safe_addstr(self.window, 0, 5, 'Input Your SSO INFO')
        self.window.bkgd(' ', curses.color_pair(5))

        self.padding_top = 2
        self.padding_left = 2

        self.input_label_idx = 0

        self.id_input_label = InputLabel(self.window, self.padding_left, 'Your NHN SSO ID: ', sso_id)
        self.pw_input_label = InputLabel(self.window, self.padding_left, 'Your NHN SSO PW: ', sso_pw)

        self.input_labels = [self.id_input_label, self.pw_input_label]

        self.id_input_label.print_label(self.padding_top, self.padding_left)
        self.pw_input_label.print_label(self.padding_top + 2, self.padding_left)

        self._move_cursor(0)

    def _move_cursor(self, delta):
        self.input_label_idx = (self.input_label_idx + delta) % len(self.input_labels)
        input_label = self.input_labels[self.input_label_idx]
        self.window.move(self.padding_top + self.input_label_idx * 2, input_label.x)

    def _process_key(self, key):
        self.input_labels[self.input_label_idx].process_key(key)

    def process(self):
        while True:
            try:
                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                elif c == curses.KEY_UP:
                    self._move_cursor(-1)
                elif c == curses.KEY_DOWN:
                    self._move_cursor(+1)
                elif c == ord('\n'):
                    if not self.id_input_label.value:
                        logger.info('no value')
                    elif not self.pw_input_label.value:
                        logger.info('no value')
                    else:
                        return {
                            'sso_id': self.id_input_label.value,
                            'sso_pw': self.pw_input_label.value
                        }
                else:
                    self._process_key(c)
            except KeyboardInterrupt:
                return None


class ServerPopupWindow:
    def __init__(self, context, server_manager, host=None, description=None, tags=None):
        h, w, y, x = calc_popup_dims(context, desired_width=100, desired_height=12)
        self.context = context
        self.server_manager = server_manager
        self.original_host = host
        self.window = curses.newwin(h, w, y, x)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        curses.curs_set(0)

        if self.original_host is None:
            safe_addstr(self.window, 0, 5, 'Register')
        else:
            safe_addstr(self.window, 0, 5, 'Modify')
        self.window.bkgd(' ', curses.color_pair(5))

        self.padding_top = 2
        self.padding_left = 2

        self.host_input_label = InputLabel(self.window, self.padding_left, 'Host :', host)
        self.description_input_label = InputLabel(self.window, self.padding_left, 'Description :', description)
        self.tags_input_label = InputLabel(self.window, self.padding_left, 'Tags :', '' if tags is None else ' '.join(tags))
        self.input_labels = [self.host_input_label, self.description_input_label, self.tags_input_label]
        self.input_label_idx = 0

        self.host_input_label.print_label(self.padding_top, self.padding_left)
        self.description_input_label.print_label(self.padding_top + 2, self.padding_left)
        self.tags_input_label.print_label(self.padding_top + 4, self.padding_left)

        self.input_labels[self.input_label_idx].set_active(True)
        self._move_cursor(0)

    def _move_cursor(self, delta):
        self.input_labels[self.input_label_idx].set_active(False)

        self.input_label_idx = (self.input_label_idx + delta) % len(self.input_labels)

        self.input_labels[self.input_label_idx].set_active(True)

        input_label = self.input_labels[self.input_label_idx]
        self.window.move(self.padding_top + self.input_label_idx * 2, input_label.min_x + input_label.cursor_pos)

    def _process_key(self, key):
        self.input_labels[self.input_label_idx].process_key(key)

    def _is_duplicated_host_exists(self):
        return self.server_manager.is_duplicated_host(
            self.host_input_label.value,
            self.original_host
        )

    def process(self):
        while True:
            try:
                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                elif c == curses.KEY_UP:
                    self._move_cursor(-1)
                elif c == curses.KEY_DOWN:
                    self._move_cursor(+1)
                elif c == ord('\n'):
                    if not self._is_duplicated_host_exists():
                        return {
                            'host': self.host_input_label.value,
                            'description': self.description_input_label.value,
                            'tags': list(filter(lambda s: s != '', re.split(',| ', self.tags_input_label.value)))
                        }
                    else:
                        safe_addstr(self.window, self.padding_top + 1, self.padding_left, 'Duplicated Host !!!', curses.color_pair(4))
                        self.window.getch()
                        safe_addstr(self.window, self.padding_top + 1, self.padding_left, '                         ')
                        self._move_cursor(0)
                else:
                    self._process_key(c)
            except KeyboardInterrupt:
                return None


class CommandPromptWindow:
    def __init__(self, context):
        self.context = context
        self.input_value = ''
        self.window = curses.newwin(1, context.cols, context.rows - 1, 0)
        self.window.keypad(True)
        curses.curs_set(0)
        self._render()

    def _render(self):
        self.window.clear()
        text = ':' + self.input_value + '_'
        padded = text.ljust(max(1, self.context.cols - 1))
        safe_addstr(self.window, 0, 0, padded, curses.color_pair(5))
        self.window.refresh()

    def process(self):
        while True:
            try:
                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                elif c == 27:
                    return None
                elif c == ord('\n'):
                    return self.input_value.strip()
                elif c in (8, 127, curses.KEY_BACKSPACE):
                    if self.input_value:
                        self.input_value = self.input_value[:-1]
                        self._render()
                elif 32 <= c <= 126:
                    self.input_value += chr(c)
                    self._render()
            except KeyboardInterrupt:
                return None
