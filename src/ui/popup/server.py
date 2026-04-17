#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import logging
import re

from ui.util import safe_addstr, calc_popup_dims
from ui.panel import InputLabel
from core import ResizeRequested

logger = logging.getLogger('gwkit')


class ServerPopup:
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


class CommandPrompt:
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
