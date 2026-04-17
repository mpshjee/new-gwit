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
            n_label = '[ctrl-n]: add to group'
            d_label = '[ctrl-d]: remove from group'
        else:
            n_label = '[ctrl-n]: register server'
            d_label = '[ctrl-d]: delete server'
        safe_addstr(self.window, 1, 2, '[/]: change user,  [,]: change rlogin/ssh,  [ctrl-g]: select group')
        safe_addstr(self.window, 2, 2, n_label + '     ' + d_label)
        safe_addstr(self.window, 3, 2, '[ctrl-e]: modify server           [ctrl-c]: quit or close popup window')
        safe_addstr(self.window, 4, 2, '[ctrl-r]: reset keyword')
        safe_addstr(self.window, 5, 2, '[:]: command mode (e.g., :all, :group <name>, :quit)')
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
    def __init__(self, ui, app, server_manager, y, height):
        self.ui = ui
        self.app = app
        self.server_manager = server_manager
        self.height = height
        self.window = curses.newwin(height, ui.cols, y, 0)
        self.window.scrollok(True)

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
