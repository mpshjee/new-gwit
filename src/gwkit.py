#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import logging
import os
import sys

from config import ResizeRequested, kinit_password
from state import Context, UserState
from data import ServerManager, ServerGroupManager
from fetch import init_server_list
from ui import (HelpPanel, GroupContextPanel, UserPanel, KeywordPanel, ServerListPanel,
                ServerPopup, CommandPrompt, show_status_message,
                GroupSelectPopup, AddServerToGroupPopup)
from ui.layout import VerticalLayout

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
        return 'open_groups', None
    elif cmd == 'all':
        context.active_group_name = ''
        return 'ok', None
    elif cmd == 'group':
        if not args:
            return 'error', 'usage: :group <group_name>'
        name = args[0]
        if server_group_manager is not None and name not in server_group_manager.groups:
            return 'error', 'group not found: ' + name
        context.active_group_name = name
        return 'ok', None
    elif cmd in ('quit', 'q'):
        return 'quit', None
    else:
        return 'error', 'unknown command: ' + cmd


def rebuild_all_windows(stdscr, context, user_state, server_manager, server_group_manager):
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
        return None, None, None, None, None

    layout = VerticalLayout(rows, cols)
    help_slot = layout.add(context.top_help_rows)
    group_ctx_slot = layout.add(context.group_context_rows)
    user_slot = layout.add(context.top_win_rows)
    list_slot = layout.fill()

    help_win = HelpPanel(context, *help_slot)
    group_ctx_win = GroupContextPanel(context, *group_ctx_slot)
    user_win = UserPanel(context, user_state, *user_slot)
    keyword_win = KeywordPanel(context, *user_slot)
    server_manager.list_height = list_slot[1]
    server_manager.filter()
    server_list_win = ServerListPanel(context, server_manager, *list_slot)
    server_list_win.refresh()
    keyword_win.refresh()
    return help_win, group_ctx_win, user_win, server_list_win, keyword_win


def _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager):
    new_wins = rebuild_all_windows(stdscr, context, user_state, server_manager, server_group_manager)
    wins['help'], wins['group_ctx'], wins['user'], wins['list'], wins['keyword'] = new_wins
    return wins['keyword'] is not None


def _handle_command_mode(wins, stdscr, context, user_state, server_manager, server_group_manager):
    cmd_str, resized = run_popup(lambda: CommandPrompt(context).process())
    if resized:
        if not _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager):
            return
    elif cmd_str is not None:
        result, message = execute_command(cmd_str, context, server_group_manager)
        if result == 'quit':
            curses.endwin()
            server_manager.save_to_json()
            server_group_manager.save()
            print('Goodbye :)')
            sys.exit()
        elif result == 'error':
            show_status_message(context, 'error: ' + message)
        elif result == 'open_groups':
            _handle_group_select(wins, stdscr, context, user_state, server_manager, server_group_manager)
            return
        elif result == 'ok':
            server_manager.filter()
            wins['list'].refresh()
            wins['group_ctx'].refresh()
        wins['help'].refresh()


def _handle_modify_server(wins, stdscr, context, user_state, server_manager, server_group_manager):
    current_server = server_manager.get_current_server()
    if current_server is not None:
        new_server, resized = run_popup(
            lambda: ServerPopup(context, server_manager,
                                      current_server['host'],
                                      current_server['description'],
                                      current_server['tags']).process())
        if resized:
            if not _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager):
                return
        elif new_server is not None:
            current_server['host'] = new_server['host']
            current_server['description'] = new_server['description']
            current_server['tags'] = new_server['tags']
            server_manager.refresh_max()
    wins['list'].refresh()


def _handle_register_server(wins, stdscr, context, user_state, server_manager, server_group_manager):
    new_server, resized = run_popup(
        lambda: ServerPopup(context, server_manager).process())
    if resized:
        if not _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager):
            return
    elif new_server is not None:
        server_manager.insert_server(new_server)
        server_manager.refresh_max()
    wins['list'].refresh()


def _handle_add_to_group(wins, stdscr, context, user_state, server_manager, server_group_manager):
    non_members = server_group_manager.get_non_member_hosts(context.active_group_name, server_manager.servers)
    host, resized = run_popup(lambda: AddServerToGroupPopup(context, non_members).process())
    if resized:
        if not _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager):
            return
    elif host is not None:
        server_group_manager.add_to_group(host, context.active_group_name)
        server_group_manager.save()
        server_manager.filter()
    wins['list'].refresh()


def _handle_group_select(wins, stdscr, context, user_state, server_manager, server_group_manager):
    new_group, resized = run_popup(lambda: GroupSelectPopup(context, server_group_manager).process())
    if resized:
        if not _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager):
            return
    else:
        if new_group is not None:
            context.active_group_name = new_group
        # 팝업 안에서 현재 컨텍스트 그룹이 삭제되었을 경우 폴백
        if context.active_group_name and context.active_group_name not in server_group_manager.groups:
            context.active_group_name = ''
        server_manager.filter()
        wins['list'].refresh()
        wins['group_ctx'].refresh()
        wins['help'].refresh()


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
    curses.init_pair(8, curses.COLOR_YELLOW, -1)

    context = Context()
    user_state = UserState(context)
    server_group_manager = ServerGroupManager()
    server_manager = ServerManager(context, server_group_manager)
    server_manager.filter()

    wins = {'help': None, 'group_ctx': None, 'user': None, 'list': None, 'keyword': None}
    _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager)

    def _rebuild():
        return _do_rebuild(wins, stdscr, context, user_state, server_manager, server_group_manager)

    simple_handlers = {
        ord('/'): lambda: wins['user'].change_user(),
        ord(','): lambda: wins['user'].change_login_method(),
        ord('\\'): lambda: wins['user'].change_login_method(),
    }

    def _handle_key(c):
        handler = simple_handlers.get(c)
        if handler is not None:
            handler()
            return

        if c == ord(':'):
            _handle_command_mode(wins, stdscr, context, user_state, server_manager, server_group_manager)
            return
        elif c == 7:  # Ctrl+G: 그룹 선택 팝업
            _handle_group_select(wins, stdscr, context, user_state, server_manager, server_group_manager)
            return
        elif c == 5:  # Ctrl+E
            _handle_modify_server(wins, stdscr, context, user_state, server_manager, server_group_manager)
            return
        elif c == 14:  # Ctrl+N
            if context.active_group_name:
                _handle_add_to_group(wins, stdscr, context, user_state, server_manager, server_group_manager)
            else:
                _handle_register_server(wins, stdscr, context, user_state, server_manager, server_group_manager)
            return
        elif c == 4:  # Ctrl+D
            if context.active_group_name:
                current = server_manager.get_current_server()
                if current:
                    server_group_manager.remove_from_group(current['host'], context.active_group_name)
                    server_group_manager.save()
                    server_manager.filter()
            else:
                server_manager.delete_current_server()
                server_manager.refresh_max()
            wins['list'].refresh()
        elif c == curses.KEY_UP:
            server_manager.select_up(1)
            wins['list'].refresh()
        elif c == curses.KEY_DOWN:
            server_manager.select_down(1)
            wins['list'].refresh()
        elif c == 338:  # PageDown
            server_manager.select_down(20)
            wins['list'].refresh()
        elif c == 339:  # PageUp
            server_manager.select_up(20)
            wins['list'].refresh()
        elif c == ord('\n'):
            if server_manager.selected_server_idx >= 0:
                curses.endwin()
                server_manager.connect(user_state.get_user())
        elif c == curses.KEY_RESIZE:
            _rebuild()
        else:
            logger.info(c)
            wins['keyword'].process(c)
            server_manager.filter()
            wins['list'].refresh()

    while True:
        try:
            if wins['keyword'] is None:
                stdscr.timeout(300)
                c = stdscr.getch()
                if c == curses.KEY_RESIZE:
                    _rebuild()
                continue

            c = wins['keyword'].getch()
            _handle_key(c)
            if wins['keyword'] is not None:
                wins['keyword'].refresh()
        except KeyboardInterrupt:
            curses.endwin()
            server_manager.save_to_json()
            server_group_manager.save()
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
