#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import re

from ui.util import safe_addstr, handle_line_edit_key
from ui.widget import InputLabel  # noqa: F401 (re-export)


class HelpPanel:
    def __init__(self, ui, app, y, height):
        self.ui = ui
        self.app = app
        self.window = curses.newwin(height, ui.cols, y, 0)
        self.window.scrollok(True)
        self.refresh()

    def refresh(self):
        self.window.clear()
        self.window.border(0)
        safe_addstr(self.window, 0, 5, 'Help')
        if self.app.active_group_name:
            n_label = '[ctrl-n]: add servers to group'
            d_label = '[ctrl-d]: remove servers from group'
        else:
            n_label = '[ctrl-n]: register server'
            d_label = '[ctrl-d]: delete server'
        safe_addstr(self.window, 1, 2, '[/]: change user,  [,]: change rlogin/ssh')
        safe_addstr(self.window, 2, 2, n_label + '     ' + d_label)
        safe_addstr(self.window, 3, 2, '[ctrl-e]: modify server           [ctrl-c]: quit or close popup window')
        safe_addstr(self.window, 4, 2, '[ctrl-r]: reset keyword')
        safe_addstr(self.window, 5, 2, '[:]: command mode (e.g., :all, :group, :group <name>, :quit)')
        safe_addstr(self.window, 6, 2, '- registered server will be saved when terminated. (server_list.json)')
        safe_addstr(self.window, 7, 2, '- make "~/.kinit_passwd" to execute kinit automatically.')
        safe_addstr(self.window, 8, 2, '- enter a keyword to filter the list.')
        self.window.refresh()


class GroupContextPanel:
    def __init__(self, ui, app, y, height):
        self.ui = ui
        self.app = app
        self.window = curses.newwin(height, ui.cols, y, 0)
        self.window.scrollok(True)
        self.refresh()

    def refresh(self):
        self.window.clear()
        self.window.border(0)
        if self.app.active_group_name:
            label = 'current server group : ' + self.app.active_group_name
        else:
            label = 'current server group : all'
        safe_addstr(self.window, 1, 2, label, curses.color_pair(8))
        self.window.refresh()


class UserPanel:
    def __init__(self, ui, user_state, y, height):
        self.ui = ui
        self.user_state = user_state
        self.window = curses.newwin(height, ui.half_cols, y, 0)
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

    def refresh(self):
        self.window.clear()
        self.refresh_user_border()


class KeywordPanel:
    def __init__(self, ui, app, y, height):
        self.ui = ui
        self.app = app
        self.window = curses.newwin(height, ui.half_cols, y, ui.half_cols)
        self.window.scrollok(True)
        self.window.keypad(True)
        self.window.border(0)
        self.cursor_pos = len(self.app.keyword)
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

        available_width = max(0, self.ui.half_cols - 4 - len(prefix))
        display_width = max(available_width, len(self.app.keyword) + 5)

        if len(self.app.keyword) == 0:
            display_text = " " * max(1, display_width)
        else:
            display_text = self.app.keyword + " " * (display_width - len(self.app.keyword))

        start_x = 2 + len(prefix)
        max_x = self.ui.half_cols - 2
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
        new_value, new_pos, changed = handle_line_edit_key(key, self.app.keyword, self.cursor_pos)
        if changed:
            self.app.keyword = new_value
            self.cursor_pos = new_pos
            self.refresh_display()


class ServerListPanel:
    _PADDING = 4

    def __init__(self, ui, app, server_manager, y, height):
        self.ui = ui
        self.app = app
        self.server_manager = server_manager
        self.height = height
        self.window = curses.newwin(height, ui.cols, y, 0)
        self.window.scrollok(True)
        self.selected_server_idx = -1
        self.top = 0
        self.bottom = 0
        self.max_host = 30
        self.max_tags = 30
        self.filter()

    def filter(self):
        self.server_manager.filter()
        self.selected_server_idx = -1
        self.top = 0
        self.bottom = max(0, self.height - self._PADDING)
        self.refresh_max()

    def refresh_max(self):
        servers = self.server_manager.servers
        if servers:
            self.max_host = max(len(s['host']) for s in servers)
            self.max_tags = max(len(', '.join(s['tags'])) for s in servers)
        else:
            self.max_host = 30
            self.max_tags = 30

    def select_up(self, delta):
        self.selected_server_idx -= delta
        if self.selected_server_idx < 0:
            self.selected_server_idx = 0

        if self.selected_server_idx < self.top:
            scroll = self.top - self.selected_server_idx
            self.top -= scroll
            self.bottom -= scroll

    def select_down(self, delta):
        filtered = self.server_manager.filtered_servers
        self.selected_server_idx += delta
        if self.selected_server_idx > len(filtered) - 1:
            self.selected_server_idx = len(filtered) - 1

        if self.selected_server_idx > self.bottom:
            scroll = self.selected_server_idx - self.bottom
            self.top += scroll
            self.bottom += scroll

    def get_current_server(self):
        if self.selected_server_idx < 0:
            return None
        filtered = self.server_manager.filtered_servers
        if self.selected_server_idx >= len(filtered):
            return None
        return filtered[self.selected_server_idx]

    def delete_current_server(self):
        current = self.get_current_server()
        if current is None:
            return
        self.server_manager.delete_server(current['host'])
        self.filter()

    def _print_color_text(self, text, index, y, x, width):
        max_y, max_x = self.window.getmaxyx()
        if y < 0 or y >= max_y:
            return

        keywords = list(map(lambda k: k.upper(), self.app.keyword.rstrip().split(' ')))
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
            if index == self.selected_server_idx:
                color_index += 1

            if word.upper() in keywords:
                color_index += 2

            safe_addstr(self.window, y, x + text_length, word, curses.color_pair(color_index))
            text_length += len(word)

        if width > 0 and text_length < width:
            safe_addstr(self.window, y, x + text_length, ''.ljust(width - text_length), curses.color_pair(color_index))

    def refresh(self):
        DEFAULT_PAD_LEN = 5
        HOST_X = DEFAULT_PAD_LEN
        TAGS_X = self.max_host + DEFAULT_PAD_LEN * 2
        DESC_X = self.max_host + self.max_tags + DEFAULT_PAD_LEN * 3

        self.window.clear()
        self.window.border(0)
        safe_addstr(self.window, 0, HOST_X, 'Host')
        safe_addstr(self.window, 0, TAGS_X, 'Tags')
        safe_addstr(self.window, 0, DESC_X, 'Description')

        max_y = self.window.getmaxyx()[0]
        for (index, server) in enumerate(self.server_manager.filtered_servers):
            if index < self.top:
                continue

            if index > self.bottom:
                break

            row_y = index - self.top + 2
            if row_y >= max_y - 1:
                break

            self._print_color_text(server['host'], index, row_y, HOST_X, self.max_host + DEFAULT_PAD_LEN)
            self._print_color_text(', '.join(server['tags']), index, row_y, TAGS_X, self.max_tags + DEFAULT_PAD_LEN)
            self._print_color_text(server['description'], index, row_y, DESC_X, -1)
        self.window.refresh()
