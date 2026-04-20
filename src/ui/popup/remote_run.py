#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import collections
import curses
import fcntl
import os
import pipes
import select
import subprocess
import time

from config import ResizeRequested
from ui.util import safe_addstr, calc_popup_dims, handle_line_edit_key


class RemoteCommandOutputPopup(object):
    def __init__(self, ui, user_state, host):
        self.ui = ui
        self.user = user_state.get_user()
        self.host = host
        self.proc = None
        self.buffer = collections.deque(maxlen=5000)

        h, w, y, x = calc_popup_dims(ui, desired_width=ui.cols - 2, desired_height=ui.rows - 2)
        self.h = h
        self.w = w
        self.window = curses.newwin(h, w, y, x)
        self.window.border(0)
        self.window.scrollok(False)
        self.window.keypad(True)
        self.window.bkgd(' ', curses.color_pair(5))

        # 출력 표시 가능 행 수: 상단 border + 하단 hint 행 + 하단 border 제외
        self._content_h = h - 3
        self._content_w = w - 4

    def _render_frame(self, title, hint=''):
        self.window.clear()
        self.window.border(0)
        safe_addstr(self.window, 0, 2, title[:self.w - 4], curses.color_pair(5))
        if hint:
            safe_addstr(self.window, self.h - 2, self.w - len(hint) - 3, hint, curses.color_pair(5))

    def _prompt_command(self):
        """명령어 입력 단계. 입력된 명령어 문자열 또는 None(취소) 반환."""
        hint = '[enter] run  [esc] cancel'
        self._render_frame('[{0}] Run remote command'.format(self.host), hint)

        value = ''
        cursor_pos = 0
        self.window.nodelay(False)
        curses.curs_set(1)

        try:
            while True:
                disp = 'Command: ' + value[:cursor_pos] + '_' + value[cursor_pos:]
                safe_addstr(self.window, 2, 2, disp.ljust(self._content_w + 2), curses.color_pair(6))
                self.window.refresh()

                c = self.window.getch()
                if c == curses.KEY_RESIZE:
                    raise ResizeRequested()
                elif c == ord('\n'):
                    return value.strip() if value.strip() else None
                elif c == 27:  # ESC
                    return None
                else:
                    value, cursor_pos, _ = handle_line_edit_key(c, value, cursor_pos)
        finally:
            curses.curs_set(0)

    def _append_lines(self, data):
        for line in data.splitlines():
            self.buffer.append(line.rstrip('\r'))

    def _render_output(self, cmd, finished=False):
        self.window.clear()
        self.window.border(0)

        title = '[{0}] $ {1}'.format(self.host, cmd)
        safe_addstr(self.window, 0, 2, title[:self.w - 4], curses.color_pair(5))

        hint = '[any key] close' if finished else '[q/esc] quit'
        safe_addstr(self.window, self.h - 2, self.w - len(hint) - 3, hint, curses.color_pair(5))

        lines = list(self.buffer)[-self._content_h:]
        for i, line in enumerate(lines):
            safe_addstr(self.window, i + 1, 2, line[:self._content_w], curses.color_pair(6))

        self.window.refresh()

    def _wait_any_key(self):
        self.window.nodelay(False)
        while True:
            c = self.window.getch()
            if c == curses.KEY_RESIZE:
                raise ResizeRequested()
            if c != -1:
                break

    def _run_command(self, cmd):
        """SSH 프로세스 실행 및 출력 스트리밍 단계."""
        # stdbuf -oL: 파이프에서도 라인 버퍼링 강제 (tail -f 등 지연 방지)
        # pipes.quote: Python 2 쉘 이스케이프
        remote_cmd = 'stdbuf -oL bash -c {0}'.format(pipes.quote(cmd))
        ssh_args = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'BatchMode=yes',
            '{0}@{1}'.format(self.user, self.host),
            remote_cmd,
        ]
        try:
            self.proc = subprocess.Popen(
                ssh_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except OSError as e:
            self.buffer.append('[error] failed to launch ssh: {0}'.format(str(e)))
            self._render_output(cmd, finished=True)
            self._wait_any_key()
            return

        fd = self.proc.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.window.nodelay(True)
        self._render_output(cmd)

        while True:
            c = self.window.getch()
            if c == curses.KEY_RESIZE:
                raise ResizeRequested()
            if c in (27, ord('q'), 3):  # ESC / q / Ctrl+C
                break

            readable, _, _ = select.select([self.proc.stdout], [], [], 0.05)
            if readable:
                try:
                    data = os.read(fd, 4096)
                except (OSError, IOError):
                    data = ''
                if data:
                    self._append_lines(data)
                    self._render_output(cmd)
                else:
                    # EOF: 프로세스 종료 대기 후 반환 코드 표시
                    rc = self.proc.wait()
                    self.buffer.append('[exited rc={0}]'.format(rc))
                    self._render_output(cmd, finished=True)
                    self.window.nodelay(False)
                    self._wait_any_key()
                    break

    def _cleanup(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            deadline = time.time() + 2.0
            while self.proc.poll() is None and time.time() < deadline:
                time.sleep(0.05)
            if self.proc.poll() is None:
                self.proc.kill()

    def process(self):
        try:
            cmd = self._prompt_command()
            if cmd:
                self._run_command(cmd)
        finally:
            self._cleanup()
            self.window.erase()
            self.window.refresh()
        return None
