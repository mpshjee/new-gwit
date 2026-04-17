#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses

from ui.util import safe_addstr, calc_popup_dims
from core import ResizeRequested


class GroupSelectPopup:
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


class AddServerToGroupPopup:
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
