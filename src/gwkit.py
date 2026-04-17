#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import logging
import os
import sys

from core import Context, UserState, ServerManager, ResizeRequested, kinit_password, init_server_list
from ui import (HelpWindow, UserWindow, KeywordWindow, ServerListWindow,
                ServerPopupWindow, CommandPromptWindow, show_status_message)

logger = logging.getLogger('gwkit')
logger.addHandler(logging.FileHandler('gwkit.log'))
logger.setLevel(logging.DEBUG)


def run_popup(popup_factory):
    try:
        return popup_factory(), False
    except ResizeRequested:
        return None, True


def execute_command(cmd_str, context, server_group_manager=None):
    parts = cmd_str.split()
    if not parts:
        return 'ok', None

    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == 'groups':
        context.view_mode = 'group_list'
        return 'ok', None
    elif cmd == 'all':
        context.view_mode = 'all'
        context.active_group_name = ''
        return 'ok', None
    elif cmd == 'group':
        if not args:
            return 'error', 'usage: :group <group_name>'
        name = args[0]
        if server_group_manager is not None and name not in server_group_manager.groups:
            return 'error', 'group not found: ' + name
        context.view_mode = 'group_detail'
        context.active_group_name = name
        return 'ok', None
    elif cmd in ('quit', 'q'):
        return 'quit', None
    else:
        return 'error', 'unknown command: ' + cmd


def rebuild_all_windows(stdscr, context, user_state, server_manager):
    stdscr.clear()
    rows, cols = stdscr.getmaxyx()
    context.update_dimensions(rows, cols)

    if context.is_too_small():
        msg = 'Terminal too small (min {}x{})'.format(Context.MIN_COLS, Context.MIN_ROWS)
        try:
            stdscr.addstr(0, 0, msg[:cols - 1] if cols > 1 else '')
        except curses.error:
            pass
        stdscr.refresh()
        return None, None, None, None

    help_win = HelpWindow(context)
    user_win = UserWindow(context, user_state)
    keyword_win = KeywordWindow(context)
    server_manager.filter()
    server_list_win = ServerListWindow(context, server_manager)
    server_list_win.refresh()
    keyword_win.refresh()
    return help_win, user_win, server_list_win, keyword_win


def main(stdscr):
    curses.noecho()
    curses.cbreak()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(0, curses.COLOR_WHITE, -1)
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_RED, curses.COLOR_YELLOW)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_WHITE)

    context = Context()
    user_state = UserState(context)
    server_manager = ServerManager(context)
    server_manager.filter()

    help_win, user_win, server_list_win, keyword_win = rebuild_all_windows(
        stdscr, context, user_state, server_manager)

    while True:
        try:
            if keyword_win is None:
                stdscr.timeout(300)
                c = stdscr.getch()
                if c == curses.KEY_RESIZE:
                    help_win, user_win, server_list_win, keyword_win = rebuild_all_windows(
                        stdscr, context, user_state, server_manager)
                continue

            c = keyword_win.getch()
            if c == ord(':'):
                cmd_str, resized = run_popup(lambda: CommandPromptWindow(context).process())
                if resized:
                    help_win, user_win, server_list_win, keyword_win = rebuild_all_windows(
                        stdscr, context, user_state, server_manager)
                    if keyword_win is None:
                        continue
                    server_list_win.refresh()
                    keyword_win.refresh()
                    continue

                if cmd_str is not None:
                    result, message = execute_command(cmd_str, context)
                    if result == 'quit':
                        curses.endwin()
                        server_manager.save_to_json()
                        print('Goodbye :)')
                        sys.exit()
                    elif result == 'error':
                        show_status_message(context, 'error: ' + message)
                    elif result == 'ok':
                        help_win.refresh()

                server_list_win.refresh()
                keyword_win.refresh()
                continue
            elif c == ord('/'):
                user_win.change_user()
            elif c == ord(','):
                user_win.change_login_method()
            elif c == ord('\\'):
                user_win.change_login_method()
            elif c == curses.KEY_UP:
                server_manager.select_up(1)
                server_list_win.refresh()
            elif c == curses.KEY_DOWN:
                server_manager.select_down(1)
                server_list_win.refresh()
            elif c == ord('\n'):
                if server_manager.selected_server_idx >= 0:
                    curses.endwin()
                    server_manager.connect(user_state.get_user())
            elif c == 338:
                server_manager.select_down(20)
                server_list_win.refresh()
            elif c == 339:
                server_manager.select_up(20)
                server_list_win.refresh()
            elif c == 4:
                server_manager.delete_current_server()
                server_manager.refresh_max()
                server_list_win.refresh()
            elif c == 5:
                current_server = server_manager.get_current_server()
                if current_server is not None:
                    new_server, resized = run_popup(
                        lambda: ServerPopupWindow(context, server_manager,
                                                  current_server['host'],
                                                  current_server['description'],
                                                  current_server['tags']).process())
                    if resized:
                        help_win, user_win, server_list_win, keyword_win = rebuild_all_windows(
                            stdscr, context, user_state, server_manager)
                        if keyword_win is None:
                            continue
                    elif new_server is not None:
                        current_server['host'] = new_server['host']
                        current_server['description'] = new_server['description']
                        current_server['tags'] = new_server['tags']
                        server_manager.refresh_max()
                server_list_win.refresh()
            elif c == 14:
                new_server, resized = run_popup(
                    lambda: ServerPopupWindow(context, server_manager).process())
                if resized:
                    help_win, user_win, server_list_win, keyword_win = rebuild_all_windows(
                        stdscr, context, user_state, server_manager)
                    if keyword_win is None:
                        continue
                elif new_server is not None:
                    server_manager.insert_server(new_server)
                    server_manager.refresh_max()
                server_list_win.refresh()
            elif c == curses.KEY_RESIZE:
                help_win, user_win, server_list_win, keyword_win = rebuild_all_windows(
                    stdscr, context, user_state, server_manager)
                if keyword_win is None:
                    continue
            else:
                logger.info(c)
                keyword_win.process(c)
                server_manager.filter()
                server_list_win.refresh()

            keyword_win.refresh()
        except KeyboardInterrupt:
            curses.endwin()
            server_manager.save_to_json()
            print('Goodbye :)')
            sys.exit()


if __name__ == '__main__':
    is_init = sys.argv
    if len(is_init) == 1:
        pass
    elif is_init[1] == "init":
        init_server_list()

    if os.path.exists(kinit_password):
        os.system('cat {0} | kinit'.format(kinit_password))
    else:
        os.system('kinit')
    curses.wrapper(main)
