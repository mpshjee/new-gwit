#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import getpass
import sys


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


def print_banner():
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


def prompt_credentials():
    sso_id = raw_input('SSO ID : ')
    sso_pw = getpass.getpass('SSO PW : ')
    return sso_id, sso_pw


def print_progress(iteration, total, prefix='', suffix='', decimals=1, barLength=100):
    formatStr = "{0:." + str(decimals) + "f}"
    percent = formatStr.format(100 * (iteration / float(total)))
    filledLength = int(round(barLength * iteration / float(total)))
    bar = (bcolors.OKBLUE + '▇' + bcolors.ENDC) * filledLength + '-' * (barLength - filledLength)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percent, '%', suffix)),
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()
