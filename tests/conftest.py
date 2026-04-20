#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), 'src')
sys.path.insert(0, _SRC)

import pytest


@pytest.fixture
def isolated_group_store(monkeypatch, tmp_path):
    import data.server_group_manager as sgm
    monkeypatch.setattr(sgm, 'server_groups_json_file', str(tmp_path / 'groups.json'))
    yield tmp_path


@pytest.fixture
def isolated_server_store(monkeypatch, tmp_path):
    import data.server_manager as sm
    monkeypatch.setattr(sm, 'server_list_json_file', str(tmp_path / 'servers.json'))
    yield tmp_path
