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
        if self.context.active_group_name:
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
        new_value, new_pos, changed = handle_line_edit_key(key, self.context.keyword, self.cursor_pos)
        if changed:
            self.context.keyword = new_value
            self.cursor_pos = new_pos
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
        ctx_label = '[group: {}]'.format(self.context.active_group_name) if self.context.active_group_name else '[all]'
        safe_addstr(self.window, 0, 2, ctx_label, curses.color_pair(8))
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
        new_value, new_pos, changed = handle_line_edit_key(key, self.value, self.cursor_pos)
        if changed:
            self.value = new_value
            self.cursor_pos = new_pos
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
        self.refresh_display()


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


class GroupSelectPopupWindow:
    ALL_LABEL = '[all servers]'

    def __init__(self, context, server_group_manager):
        self.context = context
        self.server_group_manager = server_group_manager
        self.selected_idx = 0
        self.scroll_top = 0

        h, w, y, x = calc_popup_dims(context, desired_width=60, desired_height=20)
        self.h = h
        self.w = w
        self.window = curses.newwin(h, w, y, x)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        curses.curs_set(0)
        self.window.bkgd(' ', curses.color_pair(5))
        self.max_visible = max(1, h - 5)
        self._render()

    def _entries(self):
        return [self.ALL_LABEL] + self.server_group_manager.get_group_names()

    def _render(self):
        self.window.clear()
        self.window.border(0)
        safe_addstr(self.window, 0, 2, 'Select Group  [ctrl-n]: create  [ctrl-d]: delete', curses.color_pair(5))
        entries = self._entries()
        for i in range(self.max_visible):
            y = i + 2
            idx = self.scroll_top + i
            if idx >= len(entries):
                break
            label = entries[idx].ljust(self.w - 4)
            color = curses.color_pair(1) if idx == self.selected_idx else curses.color_pair(5)
            safe_addstr(self.window, y, 2, label, color)
        if len(entries) == 1:
            safe_addstr(self.window, 3, 2, '(No groups. Ctrl+N to create.)', curses.color_pair(5))
        self.window.refresh()

    def _prompt_name(self, prompt_text):
        prompt_y = self.max_visible + 3
        value = ''
        while True:
            display = prompt_text + value + '_'
            safe_addstr(self.window, prompt_y, 2, display.ljust(self.w - 4), curses.color_pair(6))
            self.window.refresh()
            c = self.window.getch()
            if c == curses.KEY_RESIZE:
                raise ResizeRequested()
            elif c == ord('\n'):
                safe_addstr(self.window, prompt_y, 2, ' ' * (self.w - 4), curses.color_pair(5))
                return value.strip()
            elif c == 27:
                safe_addstr(self.window, prompt_y, 2, ' ' * (self.w - 4), curses.color_pair(5))
                return None
            elif c in (8, 127, curses.KEY_BACKSPACE):
                if value:
                    value = value[:-1]
            elif 32 <= c <= 126:
                value += chr(c)

    def process(self):
        while True:
            try:
                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                entries = self._entries()
                if c == curses.KEY_UP:
                    if self.selected_idx > 0:
                        self.selected_idx -= 1
                        if self.selected_idx < self.scroll_top:
                            self.scroll_top = self.selected_idx
                        self._render()
                elif c == curses.KEY_DOWN:
                    if self.selected_idx < len(entries) - 1:
                        self.selected_idx += 1
                        if self.selected_idx >= self.scroll_top + self.max_visible:
                            self.scroll_top = self.selected_idx - self.max_visible + 1
                        self._render()
                elif c == ord('\n'):
                    if not entries:
                        return None
                    selected = entries[self.selected_idx]
                    return '' if selected == self.ALL_LABEL else selected
                elif c == 14:  # Ctrl+N: 그룹 생성
                    name = self._prompt_name('New group name: ')
                    if name:
                        self.server_group_manager.create_group(name)
                        self.server_group_manager.save()
                    self._render()
                elif c == 4:  # Ctrl+D: 그룹 삭제 (all 항목 제외)
                    if self.selected_idx > 0:
                        target = entries[self.selected_idx]
                        self.server_group_manager.delete_group(target)
                        self.server_group_manager.save()
                        self.selected_idx = min(self.selected_idx, len(self._entries()) - 1)
                    self._render()
                elif c in (27, 3):  # ESC or Ctrl+C
                    return None
            except KeyboardInterrupt:
                return None


class AddServerToGroupPopupWindow:
    def __init__(self, context, non_member_servers):
        self.all_servers = non_member_servers
        self.filtered = list(non_member_servers)
        self.selected_idx = 0
        self.keyword = ''
        self.scroll_top = 0

        h, w, y, x = calc_popup_dims(context, desired_width=100, desired_height=20)
        self.window = curses.newwin(h, w, y, x)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        curses.curs_set(0)
        self.window.bkgd(' ', curses.color_pair(5))
        safe_addstr(self.window, 0, 5, 'Add Server to Group')
        self.max_visible = max(1, h - 5)
        self._render()

    def _filter(self):
        if not self.keyword:
            self.filtered = list(self.all_servers)
        else:
            kw = self.keyword.upper()
            self.filtered = [s for s in self.all_servers
                             if kw in s['host'].upper() or kw in s['description'].upper()]
        self.selected_idx = 0
        self.scroll_top = 0

    def _render(self):
        safe_addstr(self.window, 1, 2, ('Search: ' + self.keyword + '_').ljust(50), curses.color_pair(7))
        for i in range(self.max_visible):
            y = i + 3
            idx = self.scroll_top + i
            if idx >= len(self.filtered):
                safe_addstr(self.window, y, 2, ' ' * 94, curses.color_pair(5))
                continue
            s = self.filtered[idx]
            text = (s['host'] + '  ' + s['description'])[:94].ljust(94)
            color = curses.color_pair(1) if idx == self.selected_idx else curses.color_pair(7)
            safe_addstr(self.window, y, 2, text, color)
        self.window.refresh()

    def process(self):
        while True:
            try:
                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                elif c == curses.KEY_UP:
                    if self.selected_idx > 0:
                        self.selected_idx -= 1
                        if self.selected_idx < self.scroll_top:
                            self.scroll_top = self.selected_idx
                        self._render()
                elif c == curses.KEY_DOWN:
                    if self.selected_idx < len(self.filtered) - 1:
                        self.selected_idx += 1
                        if self.selected_idx >= self.scroll_top + self.max_visible:
                            self.scroll_top = self.selected_idx - self.max_visible + 1
                        self._render()
                elif c == ord('\n'):
                    if self.filtered and 0 <= self.selected_idx < len(self.filtered):
                        return self.filtered[self.selected_idx]['host']
                elif c in (8, 127, curses.KEY_BACKSPACE):
                    if self.keyword:
                        self.keyword = self.keyword[:-1]
                        self._filter()
                        self._render()
                elif c in (27, 3):  # ESC or Ctrl+C
                    return None
                elif 32 <= c <= 126:
                    self.keyword += chr(c)
                    self._filter()
                    self._render()
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
