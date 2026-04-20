#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ui.layout import VerticalLayout


class TestVerticalLayout:
    def test_add_returns_start_y_and_height(self):
        layout = VerticalLayout(rows=24, cols=80)
        y, h = layout.add(3)
        assert y == 0
        assert h == 3

    def test_add_accumulates_y(self):
        layout = VerticalLayout(rows=24, cols=80)
        layout.add(3)
        y, h = layout.add(10)
        assert y == 3
        assert h == 10

    def test_fill_takes_remaining_rows(self):
        layout = VerticalLayout(rows=24, cols=80)
        layout.add(10)
        y, h = layout.fill()
        assert y == 10
        assert h == 14

    def test_fill_minimum_height_is_one(self):
        layout = VerticalLayout(rows=24, cols=80)
        layout.add(24)
        y, h = layout.fill()
        assert h == 1  # max(1, 24-24)

    def test_fill_when_overflow_still_returns_one(self):
        layout = VerticalLayout(rows=24, cols=80)
        layout.add(30)
        y, h = layout.fill()
        assert h == 1  # max(1, 24-30) = 1

    def test_multiple_adds_consecutive(self):
        layout = VerticalLayout(rows=24, cols=80)
        y0, _ = layout.add(10)
        y1, _ = layout.add(3)
        y2, _ = layout.add(3)
        assert y0 == 0
        assert y1 == 10
        assert y2 == 13
