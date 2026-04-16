#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import logging
import os
import re

logger = logging.getLogger('gwkit')


class HelpWindow:
    def __init__(self, context):
        self.window = curses.newwin(context.top_help_rows, context.cols, 0, 0)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.addstr(0, 5, 'Help')
        self.window.addstr(1, 2, '[/]: change user to rlogin, [,]: change rlogin/ssh')
        self.window.addstr(2, 2, '[ctrl-n]: register new server     [ctrl-d]: delete server')
        self.window.addstr(3, 2, '[ctrl-e]: modify server           [ctrl-c]: quit or close popup window')
        self.window.addstr(4, 2, '[ctrl-l]: load old gw file        [ctrl-r]: reset popup input')
        self.window.addstr(5, 2, '- registered server will be saved when terminated. (server_list.json)')
        self.window.addstr(6, 2, '- make "~/.kinit_passwd" to execute kinit automatically.')
        self.window.addstr(7, 2, '- enter a keyword to filter the list.')
        self.window.addstr(8, 2, '- search for hosts, tags, and descriptions using case-insensitive keywords.')
        self.window.refresh()


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
        self.window.addstr(1, 2, "user : " + self.user_state.get_user() + ", [ " + self.user_state.get_login_method() + " ]")
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
        self.window.addstr(1, 2, prefix, curses.color_pair(0))

        available_width = self.context.half_cols - 4 - len(prefix)
        display_width = max(available_width, len(self.context.keyword) + 5)

        if len(self.context.keyword) == 0:
            display_text = " " * max(1, display_width)
        else:
            display_text = self.context.keyword + " " * (display_width - len(self.context.keyword))

        start_x = 2 + len(prefix)
        for i in range(min(display_width, available_width)):
            if i < len(display_text):
                char = display_text[i]
            else:
                char = " "

            if i == self.cursor_pos:
                if char == " ":
                    self.window.addstr(1, start_x + i, "_", curses.color_pair(2) | curses.A_BOLD)
                else:
                    self.window.addstr(1, start_x + i, char, curses.color_pair(1) | curses.A_BOLD)
            else:
                if i < len(self.context.keyword):
                    self.window.addstr(1, start_x + i, char, curses.color_pair(0))
                else:
                    self.window.addstr(1, start_x + i, char, curses.color_pair(0))

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

            self.window.addstr(y, x + text_length, word, curses.color_pair(color_index))
            text_length += len(word)

        if width > 0 and text_length < width:
            self.window.addstr(y, x + text_length, ''.ljust(width - text_length), curses.color_pair(color_index))

    def refresh(self):
        sm = self.server_manager
        DEFAULT_PAD_LEN = 5
        HOST_X = DEFAULT_PAD_LEN
        TAGS_X = sm.max_host + DEFAULT_PAD_LEN * 2
        DESC_X = sm.max_host + sm.max_tags + DEFAULT_PAD_LEN * 3

        self.window.clear()
        self.window.border(0)
        self.window.addstr(0, HOST_X, 'Host')
        self.window.addstr(0, TAGS_X, 'Tags')
        self.window.addstr(0, DESC_X, 'Description')

        for (index, server) in enumerate(sm.filtered_servers):
            if index < sm.top:
                continue

            if index > sm.bottom:
                break

            self._print_color_text(server['host'], index, index - sm.top + 2, HOST_X, sm.max_host + DEFAULT_PAD_LEN)
            self._print_color_text(', '.join(server['tags']), index, index - sm.top + 2, TAGS_X, sm.max_tags + DEFAULT_PAD_LEN)
            self._print_color_text(server['description'], index, index - sm.top + 2, DESC_X, -1)
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

        self.window.addstr(self.y, self.label_x, self.prefix + " ", curses.color_pair(5))

        display_width = max(20, len(self.value) + 5)
        display_text = self.value + " " * (display_width - len(self.value))

        for i in range(display_width):
            if i < len(display_text):
                char = display_text[i]
            else:
                char = " "

            if self.is_active and i == self.cursor_pos:
                self.window.addstr(self.y, self.min_x + i, char, curses.color_pair(6))
            else:
                self.window.addstr(self.y, self.min_x + i, char, curses.color_pair(7))

    def print_label(self, y, x):
        self.y = y
        self.label_x = x

        self.window.addstr(y, x, self.prefix + " ", curses.color_pair(5))

        display_width = max(20, len(self.value) + 5)
        display_text = self.value + " " * (display_width - len(self.value))

        for i in range(display_width):
            if i < len(display_text):
                char = display_text[i]
            else:
                char = " "

            if self.is_active and i == self.cursor_pos:
                self.window.addstr(y, self.min_x + i, char, curses.color_pair(6))
            else:
                self.window.addstr(y, self.min_x + i, char, curses.color_pair(7))


class LoadTipsServerList:
    def __init__(self, context, sso_id=None, sso_pw=None):
        half_cols = int(context.cols / 2) - 50
        self.context = context
        self.window = curses.newwin(12, 100, self.context.top_help_rows + self.context.top_win_rows + 4, half_cols)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        self.window.addstr(0, 5, 'Input Your SSO INFO')
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
        while (True):
            try:
                c = self.window.getch()
                if c == curses.KEY_UP:
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


class LoadOldGwFilePopupWindow:
    def __init__(self, context):
        half_cols = int(context.cols / 2) - 50
        self.window = curses.newwin(3, 100, context.top_help_rows + context.top_win_rows + 4, half_cols)
        self.window.border(0)
        self.window.scrollok(True)
        curses.curs_set(0)

        self.window.addstr(0, 5, 'Load old gateway .known_hosts (.known_host can be omitted)')
        self.window.bkgd(' ', curses.color_pair(5))
        self.path_input_label = InputLabel(self.window, 2, 'Path :', os.path.expanduser('~'))
        self.path_input_label.set_active(True)
        self.path_input_label.print_label(1, 2)

    def process(self):
        while (True):
            try:
                c = self.window.getch()
                if c == ord('\n'):
                    return self.path_input_label.value
                else:
                    self.path_input_label.process_key(c)
            except KeyboardInterrupt:
                return None


class ServerPopupWindow:
    def __init__(self, context, server_manager, host=None, description=None, tags=None):
        half_cols = int(context.cols / 2) - 50
        self.context = context
        self.server_manager = server_manager
        self.original_host = host
        self.window = curses.newwin(12, 100, self.context.top_help_rows + self.context.top_win_rows + 4, half_cols)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        curses.curs_set(0)

        if self.original_host is None:
            self.window.addstr(0, 5, 'Register')
        else:
            self.window.addstr(0, 5, 'Modify')
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
        while (True):
            try:
                c = self.window.getch()
                if c == curses.KEY_UP:
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
                        self.window.addstr(self.padding_top + 1, self.padding_left, 'Duplicated Host !!!', curses.color_pair(4))
                        self.window.getch()
                        self.window.addstr(self.padding_top + 1, self.padding_left, '                         ')
                        self._move_cursor(0)
                else:
                    self._process_key(c)
            except KeyboardInterrupt:
                return None
