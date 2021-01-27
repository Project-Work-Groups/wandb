#
# -*- coding: utf-8 -*-
"""
static settings.
"""

import wandb

if wandb.TYPE_CHECKING:  # type: ignore
    from typing import Optional


class SettingsStatic(object):
    # TODO(jhr): figure out how to share type defs with sdk/wandb_settings.py
    _offline: Optional[bool]
    _disable_stats: Optional[bool]
    _disable_meta: Optional[bool]
    _start_time: float
    files_dir: str

    def __init__(self, config):
        object.__setattr__(self, "__dict__", dict(config))

    def __setattr__(self, name, value):
        raise AttributeError("Error: SettingsStatic is a readonly object")

    def __setitem__(self, key, val):
        raise AttributeError("Error: SettingsStatic is a readonly object")

    def keys(self):
        return self.__dict__.keys()

    def __getitem__(self, key):
        return self.__dict__[key]

    def __str__(self):
        return str(self.__dict__)
