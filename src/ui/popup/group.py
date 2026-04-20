#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses

from ui.util import safe_addstr, calc_popup_dims
from ui.widget import ScrollableList
from config import ResizeRequested


class GroupSelectPopup:
    ALL_LABEL = '[all servers]'

    def __init__(self, ui, server_group_manager):
        self.ui = ui
        self.server_group_manager = server_group_manager

        h, w, y, x = calc_popup_dims(ui, desired_width=60, desired_height=20)
        self.w = w
        self.window = curses.newwin(h, w, y, x)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        curses.curs_set(0)
        self.window.bkgd(' ', curses.color_pair(5))

        max_visible = max(1, h - 5)
        self.list = ScrollableList(self.window, start_y=2, x=2, width=w - 4, max_visible=max_visible)
        self._refresh_entries()
        self._render()

    def _refresh_entries(self):
        self.list.set_items([self.ALL_LABEL] + self.server_group_manager.get_group_names())

    def _render(self):
        self.window.clear()
        self.window.border(0)
        safe_addstr(self.window, 0, 2, 'Select Group  [ctrl-n]: create  [ctrl-d]: delete', curses.color_pair(5))
        self.list.render()
        if len(self.list.items) == 1:
            safe_addstr(self.window, 3, 2, '(No groups. Ctrl+N to create.)', curses.color_pair(5))
        self.window.refresh()

    def _prompt_name(self, prompt_text):
        prompt_y = self.list.max_visible + 3
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
        try:
            while True:
                try:
                    c = self.window.getch()
                    if c == curses.KEY_RESIZE:
                        raise ResizeRequested()
                    elif c == curses.KEY_UP:
                        self.list.select_up()
                        self._render()
                    elif c == curses.KEY_DOWN:
                        self.list.select_down()
                        self._render()
                    elif c == ord('\n'):
                        selected = self.list.get_selected()
                        if selected is None:
                            return None
                        return '' if selected == self.ALL_LABEL else selected
                    elif c == 14:  # Ctrl+N: 그룹 생성
                        name = self._prompt_name('New group name: ')
                        if name:
                            self.server_group_manager.create_group(name)
                            self.server_group_manager.save()
                        self._refresh_entries()
                        self._render()
                    elif c == 4:  # Ctrl+D: 그룹 삭제 (all 항목 제외)
                        if self.list.selected_idx > 0:
                            target = self.list.get_selected()
                            self.server_group_manager.delete_group(target)
                            self.server_group_manager.save()
                        self._refresh_entries()
                        self._render()
                    elif c in (27, 3):  # ESC or Ctrl+C
                        return None
                except KeyboardInterrupt:
                    return None
        finally:
            self.window.erase()
            self.window.refresh()


class _MultiSelectServerPopup:
    TITLE = ''
    HINT = '[space] toggle  [enter] confirm  [esc] cancel'

    def __init__(self, ui, servers):
        self.all_servers = list(servers)
        self.keyword = ''
        self._checked_hosts = set()

        h, w, y, x = calc_popup_dims(ui, desired_width=100, desired_height=20)
        self.w = w
        self.window = curses.newwin(h, w, y, x)
        self.window.border(0)
        self.window.scrollok(True)
        self.window.keypad(True)
        curses.curs_set(0)
        self.window.bkgd(' ', curses.color_pair(5))
        safe_addstr(self.window, 0, 5, self.TITLE)

        max_visible = max(1, h - 5)
        self.list = ScrollableList(
            self.window, start_y=3, x=2, width=w - 4, max_visible=max_visible,
            format_fn=lambda s: s['host'] + '  ' + s['description'],
            multi_select=True)
        self.list.set_items(list(self.all_servers))
        self._render()

    def _filter(self):
        self._sync_checked_from_list()
        if not self.keyword:
            visible = list(self.all_servers)
        else:
            kw = self.keyword.upper()
            visible = [s for s in self.all_servers
                       if kw in s['host'].upper() or kw in s['description'].upper()]
        self.list.set_items(visible)
        self.list.checked_indices = set(
            i for i, s in enumerate(visible) if s['host'] in self._checked_hosts)

    def _sync_checked_from_list(self):
        for i, s in enumerate(self.list.items):
            if i in self.list.checked_indices:
                self._checked_hosts.add(s['host'])
            else:
                self._checked_hosts.discard(s['host'])

    def _render(self):
        safe_addstr(self.window, 0, self.w - len(self.HINT) - 4, self.HINT, curses.color_pair(5))
        safe_addstr(self.window, 1, 2, ('Search: ' + self.keyword + '_').ljust(self.w - 4), curses.color_pair(7))
        self.list.render(selected_color=1, normal_color=7)
        self.window.refresh()

    def process(self):
        try:
            while True:
                try:
                    c = self.window.getch()
                    if c == curses.KEY_RESIZE:
                        raise ResizeRequested()
                    elif c == curses.KEY_UP:
                        self.list.select_up()
                        self._render()
                    elif c == curses.KEY_DOWN:
                        self.list.select_down()
                        self._render()
                    elif c == ord(' '):
                        self.list.toggle_current()
                        self._sync_checked_from_list()
                        self._render()
                    elif c == ord('\n'):
                        self._sync_checked_from_list()
                        return [s['host'] for s in self.all_servers
                                if s['host'] in self._checked_hosts]
                    elif c in (8, 127, curses.KEY_BACKSPACE):
                        if self.keyword:
                            self.keyword = self.keyword[:-1]
                            self._filter()
                            self._render()
                    elif c in (27, 3):  # ESC or Ctrl+C
                        return None
                    elif 32 < c <= 126:
                        self.keyword += chr(c)
                        self._filter()
                        self._render()
                except KeyboardInterrupt:
                    return None
        finally:
            self.window.erase()
            self.window.refresh()


class AddServerToGroupPopup(_MultiSelectServerPopup):
    TITLE = 'Add Servers to Group'


class RemoveServersFromGroupPopup(_MultiSelectServerPopup):
    TITLE = 'Remove Servers from Group'
