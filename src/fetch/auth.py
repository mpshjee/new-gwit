#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import requests


def login(sso_id, sso_pw):
    session = requests.Session()
    print('first page in tips.nhnent.com ')
    get_session_cookies = session.get('https://tips.nhnent.com')
    get_session_cookies.headers.get('set-cookie')
    get_session_cookies.cookies

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
    response = session.post(loginUrl, data=data_payload)
    if response.status_code != 200:
        print('Your sso could not be authentication.')
        quit()

    return session
