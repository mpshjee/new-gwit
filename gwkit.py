#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import curses
import logging
import os
import sys

from core import Context, UserState, ServerManager, kinit_password, init_server_list
from ui import (HelpWindow, UserWindow, KeywordWindow, ServerListWindow,
                ServerPopupWindow, LoadOldGwFilePopupWindow)

logger = logging.getLogger('gwkit')
logger.addHandler(logging.FileHandler('gwkit.log'))
logger.setLevel(logging.DEBUG)


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
    rows, cols = stdscr.getmaxyx()
    context.update_dimensions(rows, cols)

    user_state = UserState(context)
    server_manager = ServerManager(context)
    server_manager.filter()

    HelpWindow(context)
    user_win = UserWindow(context, user_state)
    server_list_win = ServerListWindow(context, server_manager)
    server_list_win.refresh()
    keyword_win = KeywordWindow(context)

    while True:
        try:
            c = keyword_win.getch()
            if c == ord('/'):
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
                    popup_win = ServerPopupWindow(context,
                                                  server_manager,
                                                  current_server['host'],
                                                  current_server['description'],
                                                  current_server['tags'])
                    new_server = popup_win.process()
                    if new_server is not None:
                        current_server['host'] = new_server['host']
                        current_server['description'] = new_server['description']
                        current_server['tags'] = new_server['tags']
                        server_manager.refresh_max()

                server_list_win.refresh()
            elif c == 14:
                popup_win = ServerPopupWindow(context, server_manager)
                new_server = popup_win.process()
                if new_server is not None:
                    server_manager.insert_server(new_server)
                    server_manager.refresh_max()

                server_list_win.refresh()
            elif c == 12:
                popup_win = LoadOldGwFilePopupWindow(context)
                known_host_path = popup_win.process()
                if known_host_path is not None:
                    server_manager.load_old_gw_file(known_host_path)

                server_list_win.refresh()
            elif c == curses.KEY_RESIZE:
                rows, cols = stdscr.getmaxyx()
                context.update_dimensions(rows, cols)
                user_win = UserWindow(context, user_state)
                server_list_win = ServerListWindow(context, server_manager)
                server_manager.filter()
                server_list_win.refresh()
                keyword_win = KeywordWindow(context)
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
