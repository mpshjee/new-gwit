#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses

from ui.util import safe_addstr, handle_line_edit_key


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


class FormInput:
    def __init__(self, window, padding_top, padding_left, fields):
        self.window = window
        self.padding_top = padding_top
        self.labels = []
        for i, (prefix, value) in enumerate(fields):
            label = InputLabel(window, padding_left, prefix, value)
            label.print_label(padding_top + i * 2, padding_left)
            self.labels.append(label)
        self.active_idx = 0
        self.labels[0].set_active(True)

    def move_cursor(self, delta):
        self.labels[self.active_idx].set_active(False)
        self.active_idx = (self.active_idx + delta) % len(self.labels)
        self.labels[self.active_idx].set_active(True)
        label = self.labels[self.active_idx]
        self.window.move(self.padding_top + self.active_idx * 2, label.min_x + label.cursor_pos)

    def process_key(self, key):
        self.labels[self.active_idx].process_key(key)

    def get_value(self, index):
        return self.labels[index].value

    def get_values(self):
        return [label.value for label in self.labels]


class ScrollableList:
    def __init__(self, window, start_y, x, width, max_visible, format_fn=None):
        self.window = window
        self.items = []
        self.start_y = start_y
        self.x = x
        self.width = width
        self.max_visible = max_visible
        self.selected_idx = 0
        self.scroll_top = 0
        self.format_fn = format_fn or (lambda item: str(item))

    def set_items(self, items):
        self.items = items
        if self.selected_idx >= len(items):
            self.selected_idx = max(0, len(items) - 1)

    def select_up(self):
        if self.selected_idx > 0:
            self.selected_idx -= 1
            if self.selected_idx < self.scroll_top:
                self.scroll_top = self.selected_idx

    def select_down(self):
        if self.selected_idx < len(self.items) - 1:
            self.selected_idx += 1
            if self.selected_idx >= self.scroll_top + self.max_visible:
                self.scroll_top = self.selected_idx - self.max_visible + 1

    def get_selected(self):
        if self.items and 0 <= self.selected_idx < len(self.items):
            return self.items[self.selected_idx]
        return None

    def render(self, selected_color=1, normal_color=5):
        for i in range(self.max_visible):
            y = self.start_y + i
            idx = self.scroll_top + i
            if idx >= len(self.items):
                safe_addstr(self.window, y, self.x, ' ' * self.width, curses.color_pair(normal_color))
                continue
            text = self.format_fn(self.items[idx])
            if len(text) > self.width:
                text = text[:self.width - 3] + '...'
            text = text.ljust(self.width)
            color = curses.color_pair(selected_color) if idx == self.selected_idx else curses.color_pair(normal_color)
            safe_addstr(self.window, y, self.x, text, color)
