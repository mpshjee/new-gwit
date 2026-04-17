#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import logging
import re

from ui.util import safe_addstr, calc_popup_dims
from ui.widget import FormInput
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

        self.form = FormInput(self.window, padding_top=2, padding_left=2, fields=[
            ('Host :', host),
            ('Description :', description),
            ('Tags :', '' if tags is None else ' '.join(tags)),
        ])

    def process(self):
        while True:
            try:
                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                elif c == curses.KEY_UP:
                    self.form.move_cursor(-1)
                elif c == curses.KEY_DOWN:
                    self.form.move_cursor(1)
                elif c == ord('\n'):
                    host_val = self.form.get_value(0)
                    if not self.server_manager.is_duplicated_host(host_val, self.original_host):
                        return {
                            'host': host_val,
                            'description': self.form.get_value(1),
                            'tags': list(filter(lambda s: s != '', re.split(',| ', self.form.get_value(2))))
                        }
                    else:
                        safe_addstr(self.window, 3, 2, 'Duplicated Host !!!', curses.color_pair(4))
                        self.window.getch()
                        safe_addstr(self.window, 3, 2, '                         ')
                        self.form.move_cursor(0)
                else:
                    self.form.process_key(c)
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

        self.form = FormInput(self.window, padding_top=2, padding_left=2, fields=[
            ('Your NHN SSO ID: ', sso_id),
            ('Your NHN SSO PW: ', sso_pw),
        ])

    def process(self):
        while True:
            try:
                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                elif c == curses.KEY_UP:
                    self.form.move_cursor(-1)
                elif c == curses.KEY_DOWN:
                    self.form.move_cursor(1)
                elif c == ord('\n'):
                    values = self.form.get_values()
                    if not values[0]:
                        logger.info('no value')
                    elif not values[1]:
                        logger.info('no value')
                    else:
                        return {'sso_id': values[0], 'sso_pw': values[1]}
                else:
                    self.form.process_key(c)
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
