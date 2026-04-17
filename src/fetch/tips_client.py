#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import json
import logging

logger = logging.getLogger('gwkit')

_POST_URL = 'https://tips.nhnent.com/config/server-groups/my/retrieve'
_GET_URL = 'https://tips.nhnent.com/config/server-groups/management/'
_POST_PARAMS = {
    'searchCategory': 'serviceOrPlatform',
    'searchText': '',
    'orderType': 1,
    'orderFieldName': 'service_name',
    'all': 'true',
}
_GET_PARAMS = {
    'formMode': '1',
    'pageNum': '1',
    'orderFieldName': 'host_name',
    'orderType': '1',
}


def list_server_groups(session):
    response = session.post(_POST_URL, json=_POST_PARAMS)
    logger.info('[init] server group list response status: %s', response.status_code)
    logger.info('[init] server group list response body: %s', response.text)
    data = response.json().get("serverGroupForManagementData").get("data")
    return [{'code': li.get('serverGroupCode'), 'service_name': li.get('serviceName')} for li in data]


def list_servers_in_group(session, server_group_code, service_name):
    url = _GET_URL + str(server_group_code)
    response = session.get(url, params=_GET_PARAMS)
    logger.info('[init] group %s response status: %s', server_group_code, response.status_code)

    dict_contents = json.loads(response.content)
    server_list = dict_contents.get('serverGroupForManagement').get('data').get('serverList')
    logger.info('[init] group %s: %d servers found', server_group_code, len(server_list))

    result = []
    for server in server_list:
        file_data = {}
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
    return result
