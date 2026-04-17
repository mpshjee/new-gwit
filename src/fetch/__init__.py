#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import getpass
import json
import logging
import os
import sys

import requests

logger = logging.getLogger('gwkit')

whatsup_url = 'whatsup.nhnent.com'

_fetch_dir = os.path.dirname(os.path.realpath(__file__))
_src_dir = os.path.dirname(_fetch_dir)
_project_root = os.path.dirname(_src_dir)
_server_list_json_file = '{0}/server_list.json'.format(_project_root)


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
    print(bcolors.OKBLUE + """
 __    __  __    __  __    __         ______    ______    ______
|  \  |  \|  \  |  \|  \  |  \       /      \  /      \  /      \\
| $$\\ | $$| $$  | $$| $$\\ | $$      |  $$$$$$\\|  $$$$$$\\|  $$$$$$\\
| $$$\\| $$| $$__| $$| $$$\\| $$      | $$___\$$| $$___\$$| $$  | $$
| $$$$\\ $$| $$    $$| $$$$\\ $$       \$$    \\  \$$    \\ | $$  | $$
| $$\$$ $$| $$$$$$$$| $$\$$ $$       _\$$$$$$\\ _\$$$$$$\\| $$  | $$
| $$ \$$$$| $$  | $$| $$ \$$$$      |  \__| $$|  \__| $$| $$__/ $$
| $$  \$$$| $$  | $$| $$  \$$$       \$$    $$ \$$    $$ \$$    $$
 \$$   \$$ \$$   \$$ \$$   \$$        \$$$$$$   \$$$$$$   \$$$$$$
""" + bcolors.ENDC)
    # sso auth
    sso_id = raw_input('SSO ID : ')
    sso_pw = getpass.getpass('SSO PW : ')

    session = requests.Session()
    print('first page in tips.nhnent.com ')
    get_session_cookies = session.get('https://tips.nhnent.com')
    cookie_result = get_session_cookies.headers.get('set-cookie')
    cookies = get_session_cookies.cookies

    html = get_session_cookies.text
    actionStartIndex = html.find('action=') + 8
    print(actionStartIndex)
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
        print('Your sso could not be authentication.')
        quit()

    cookies = get_session_cookies.cookies

    print('Fetching your server list....')

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
    print('')

    logger.info('[init] total servers collected: %d', len(result))
    logger.info('[init] saving to %s', _server_list_json_file)

    final_result = str(result).replace("\'", "\"")
    f = open(_server_list_json_file, 'w')
    f.write(final_result)
    f.close()
    logger.info('[init] save complete')
