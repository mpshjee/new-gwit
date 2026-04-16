#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import getpass
import json
import logging
import os
import sys

import requests

logger = logging.getLogger('gwkit')

# sso auth
whatsup_url = 'whatsup.nhnent.com'

# gwkit path file
script_path = os.path.dirname(os.path.realpath(__file__))
kinit_password = '{0}/.kinit_passwd'.format(script_path)
server_list_json_file = '{0}/server_list.json'.format(script_path)


class ResizeRequested(Exception):
    pass


class Context:
    MIN_ROWS = 17
    MIN_COLS = 60

    def __init__(self):
        self.user_idx = 0
        self.keyword = ''
        self.rows = 0
        self.cols = 0
        self.half_cols = 0
        self.top_help_rows = 10
        self.top_win_rows = 3
        self.login_method_idx = 1

    def update_dimensions(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.half_cols = int(cols / 2)

    def is_too_small(self):
        return self.rows < self.MIN_ROWS or self.cols < self.MIN_COLS


class UserState:
    def __init__(self, context):
        self.context = context
        self.users = ['irteam', 'irteamsu']
        self.login_methods = ['rlogin', 'ssh']

    def change_user(self):
        self.context.user_idx = (self.context.user_idx + 1) % 2

    def change_login_method(self):
        self.context.login_method_idx = (self.context.login_method_idx + 1) % 2

    def get_user(self):
        return self.users[self.context.user_idx]

    def get_login_method(self):
        return self.login_methods[self.context.login_method_idx]


class ServerManager:
    def __init__(self, context):
        self.context = context
        self.servers = []
        self.filtered_servers = []
        self.selected_server_idx = -1
        self.top = 0
        self.bottom = 0
        self.max_host = 30
        self.max_tags = 30
        self.padding = 4
        self.load_servers()

    def load_servers(self):
        if os.path.exists(server_list_json_file):
            with open(server_list_json_file, 'r') as f:
                self.servers = sorted(json.load(f), key=lambda s: s['host'])
                self.refresh_max()

    def refresh_max(self):
        if len(self.servers) > 0:
            self.max_host = max(map(lambda s: len(s['host']), self.servers))
            self.max_tags = max(map(lambda s: len(', '.join(s['tags'])), self.servers))
        else:
            self.servers = []
            self.max_host = 30
            self.max_tags = 30

    def _is_matched(self, server, keyword):
        upper_keyword = keyword.upper()

        if upper_keyword in server['host'].upper():
            return True

        if upper_keyword in server['description'].upper():
            return True

        for tag in map(lambda t: t.upper(), server['tags']):
            if upper_keyword in tag:
                return True

        return False

    def filter(self, selected_server_idx=None):
        self.filtered_servers = self.servers
        self.top = 0
        self.bottom = self.context.rows - self.padding - self.context.top_win_rows - self.context.top_help_rows

        if self.context.keyword != '':
            keywords = self.context.keyword.split(' ')
            for k in keywords:
                self.filtered_servers = list(filter(lambda s: self._is_matched(s, k), self.filtered_servers))

        if selected_server_idx is None or selected_server_idx > len(self.filtered_servers) - 1:
            self.selected_server_idx = -1
        else:
            self.selected_server_idx = selected_server_idx

    def select_up(self, delta):
        self.selected_server_idx -= delta
        if self.selected_server_idx < 0:
            self.selected_server_idx = 0

        if self.selected_server_idx < self.top:
            scroll = self.top - self.selected_server_idx
            self.top -= scroll
            self.bottom -= scroll

    def select_down(self, delta):
        self.selected_server_idx += delta
        if self.selected_server_idx > len(self.filtered_servers) - 1:
            self.selected_server_idx = len(self.filtered_servers) - 1

        if self.selected_server_idx > self.bottom:
            scroll = self.selected_server_idx - self.bottom
            self.top += scroll
            self.bottom += scroll

    def connect(self, user):
        if self.selected_server_idx < 0:
            return

        host = self.filtered_servers[self.selected_server_idx]['host']
        if self.context.login_method_idx == 0:
            ret = os.system('rlogin -l {0} {1}'.format(user, host))
            if ret != 0:
                os.system('ssh {0}@{1}'.format(user, host))
        else:
            os.system('ssh {0}@{1}'.format(user, host))

    def save_to_json(self):
        with open(server_list_json_file, 'w') as f:
            json.dump(self.servers, f)

    def insert_server(self, new_server):
        for s in self.servers:
            if s['host'] == new_server['host']:
                return

        self.servers.insert(0, new_server)
        self.filter()

    def delete_current_server(self):
        if self.selected_server_idx < 0:
            return

        deleted = self.filtered_servers.pop(self.selected_server_idx)
        self.servers = list(filter(lambda s: s['host'] != deleted['host'], self.servers))
        self.filter(self.selected_server_idx)

    def get_current_server(self):
        if self.selected_server_idx < 0:
            return None
        else:
            return self.filtered_servers[self.selected_server_idx]

    def load_old_gw_file(self, known_host_path):
        if '.known_hosts' not in known_host_path:
            known_host_path = known_host_path + '/.known_hosts'

        if not os.path.exists(known_host_path):
            return

        with open(known_host_path, 'r') as f:
            lines = f.readlines()
            for line in lines:
                chunks = line.strip().split()
                host = chunks[0].strip()
                description = ' '.join(chunks[1:])
                host = host.strip()
                self.insert_server({
                    'host': host,
                    'description': description,
                    'tags': []
                })

    def is_duplicated_host(self, host, original_host=None):
        if original_host is not None and original_host == host:
            return False

        for s in self.servers:
            if s['host'] == host:
                return True

        return False


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    YELLOW = '\033[93m'
    BALCK = '\033[30m'


def print_progress(iteration, total, prefix='', suffix='', decimals=1, barLength=100):
    formatStr = "{0:." + str(decimals) + "f}"
    percent = formatStr.format(100 * (iteration / float(total)))
    filledLength = int(round(barLength * iteration / float(total)))
    bar = (bcolors.OKBLUE + '▇' + bcolors.ENDC) * filledLength + '-' * (barLength - filledLength)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percent, '%', suffix)),
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


def init_server_list():
    print
    bcolors.OKBLUE + """
 __    __  __    __  __    __         ______    ______    ______
|  \  |  \|  \  |  \|  \  |  \       /      \  /      \  /      \\
| $$\ | $$| $$  | $$| $$\ | $$      |  $$$$$$\|  $$$$$$\|  $$$$$$\\
| $$$\| $$| $$__| $$| $$$\| $$      | $$___\$$| $$___\$$| $$  | $$
| $$$$\ $$| $$    $$| $$$$\ $$       \$$    \  \$$    \ | $$  | $$
| $$\$$ $$| $$$$$$$$| $$\$$ $$       _\$$$$$$\ _\$$$$$$\| $$  | $$
| $$ \$$$$| $$  | $$| $$ \$$$$      |  \__| $$|  \__| $$| $$__/ $$
| $$  \$$$| $$  | $$| $$  \$$$       \$$    $$ \$$    $$ \$$    $$
 \$$   \$$ \$$   \$$ \$$   \$$        \$$$$$$   \$$$$$$   \$$$$$$
""" + bcolors.ENDC
    # sso auth
    sso_id = raw_input('SSO ID : ')
    sso_pw = getpass.getpass('SSO PW : ')

    session = requests.Session()
    print
    'first page in tips.nhnent.com '
    get_session_cookies = session.get('https://tips.nhnent.com')
    cookie_result = get_session_cookies.headers.get('set-cookie')
    cookies = get_session_cookies.cookies

    html = get_session_cookies.text
    actionStartIndex = html.find('action=') + 8
    print
    actionStartIndex
    actionEndIndex = html.find('" method', actionStartIndex)

    loginUrl = html[actionStartIndex:actionEndIndex].replace('&amp;', '&')

    data_payload = {
        'x': 53,
        'y': 48,
        'language': 'ko_KR',
        'times': 'Asia/Seoul:+9',
        'username': sso_id,
        'password': sso_pw}

    print('login... ' + loginUrl)
    get_session_cookies = session.post(loginUrl, data=data_payload)
    if get_session_cookies.status_code != 200:
        print
        'Your sso could not be authentication.'
        quit()

    cookies = get_session_cookies.cookies

    print
    'Fetching your server list....'

    post_url = 'https://tips.nhnent.com/config/server-groups/my/retrieve'
    post_params = {'searchCategory': 'serviceOrPlatform', 'searchText': '', 'orderType': 1, 'orderFieldName': 'service_name', 'all': 'true'}

    get_url = 'https://tips.nhnent.com/config/server-groups/management/'
    get_params = {'formMode': '1', 'pageNum': '1', 'orderFieldName': 'host_name', 'orderType': '1'}

    post_response = session.post(post_url, json=post_params)
    logger.info('[init] server group list response status: %s', post_response.status_code)
    logger.info('[init] server group list response body: %s', post_response.text)

    post_data_list = post_response.json().get("serverGroupForManagementData").get("data")
    logger.info('[init] total server groups: %d', len(post_data_list))
    result = list()

    i = 1
    for li in post_data_list:
        server_group_code = li.get('serverGroupCode')
        service_name = li.get('serviceName')
        logger.info('[init] fetching group [%d/%d]: code=%s, service=%s',
                     i, len(post_data_list), server_group_code, service_name)

        url = get_url + str(server_group_code)
        get_response = session.get(url, params=get_params)
        logger.info('[init] group %s response status: %s', server_group_code, get_response.status_code)

        contents = get_response.content
        dict_contents = json.loads(contents)

        server_list = dict_contents.get('serverGroupForManagement').get('data').get('serverList')
        logger.info('[init] group %s: %d servers found', server_group_code, len(server_list))

        for server in server_list:
            file_data = dict()
            file_data["host"] = server.get('hostName').encode("utf-8")
            file_data["description"] = service_name.encode("utf-8")

            if server.get('tags') is None:
                file_data["tags"] = []
            else:
                tags = server.get('tags').encode("utf-8")
                file_data["tags"] = tags.split()

            logger.info('[init] server: host=%s, desc=%s, tags=%s',
                         file_data["host"], file_data["description"], file_data["tags"])
            result.append(file_data)
        print_progress(i, len(post_data_list), 'Fetch Progress:', 'Complete', 1, 50)
        i += 1
    print
    ""

    logger.info('[init] total servers collected: %d', len(result))
    logger.info('[init] saving to %s', server_list_json_file)

    final_result = str(result).replace("\'", "\"")
    f = open(server_list_json_file, 'w')
    f.write(final_result)
    f.close()
    logger.info('[init] save complete')
