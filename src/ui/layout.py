#!/usr/bin/env python2
# -*- coding: utf-8 -*-


class VerticalLayout:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.current_y = 0

    def add(self, height):
        y = self.current_y
        self.current_y += height
        return y, height

    def fill(self):
        y = self.current_y
        height = max(1, self.rows - self.current_y)
        self.current_y = self.rows
        return y, height
