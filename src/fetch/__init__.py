#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import logging
import os

from fetch import auth, cli_io, store, tips_client

logger = logging.getLogger('gwkit')

_fetch_dir = os.path.dirname(os.path.realpath(__file__))
_server_list_json_file = '{0}/server_list.json'.format(
    os.path.dirname(os.path.dirname(_fetch_dir)))


def init_server_list():
    cli_io.print_banner()
    sso_id, sso_pw = cli_io.prompt_credentials()

    session = auth.login(sso_id, sso_pw)

    server_groups = tips_client.list_server_groups(session)
    logger.info('[init] total server groups: %d', len(server_groups))

    result = []
    i = 1
    for group in server_groups:
        code = group['code']
        service_name = group['service_name']
        logger.info('[init] fetching group [%d/%d]: code=%s, service=%s',
                     i, len(server_groups), code, service_name)
        servers = tips_client.list_servers_in_group(session, code, service_name)
        result.extend(servers)
        cli_io.print_progress(i, len(server_groups), 'Fetch Progress:', 'Complete', 1, 50)
        i += 1
    print('')

    logger.info('[init] total servers collected: %d', len(result))
    logger.info('[init] saving to %s', _server_list_json_file)
    store.save_server_list(result, _server_list_json_file)
    logger.info('[init] save complete')
