#!/usr/bin/env python3
#
# Copyright (c) 2021, AT&T Intellectual Property.  All Rights Reserved
#
# SPDX-License-Identifier: LGPL-2.1-only

"""
Unit-tests for the vyatta_system_timing module.
"""
from os.path import dirname, realpath, sep, pardir
import sys, os
root = os.path.join(dirname(realpath(__file__)), "../")

from unittest.mock import MagicMock, Mock
import pytest
import importlib.machinery
import vci
loader = importlib.machinery.SourceFileLoader('vyatta_system_timing',
                            os.path.join(root, "vyatta_system_timing"))
vyatta_system_timing = loader.load_module()


g_timing_source_config = {
    "one-pps": {
        "gps-1pps": {"weighted-priority": 50},
        "ptp-1pps": {"weighted-priority": 40},
        "sma-1pps": {"weighted-priority": 30},
        "tod-1pps": {"weighted-priority": 20},
    },
    "frequency": {
        "gps":      {"weighted-priority": 50},
        "synce":    {"weighted-priority": 40},
        "ptp":      {"weighted-priority": 30},
        "sma":      {"weighted-priority": 20},
        "bits":     {"weighted-priority": 10},
    },
}


def setup():
    pass


def teardown():
    pass


def test_set_config_1pps_GPS():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "timing-source": {
                    "one-pps": {"gps-1pps": {"weighted-priority": 25}}
                }
            }
        }
    }
    configInst.set(input)
    configInst.timing_util.set_1pps_priority.assert_any_call("GPS-1PPS", 3)

    configs = configInst.get()
    timing_source_config = configs["vyatta-system-v1:system"][
        "vyatta-system-timing-v1:timing"
    ]["timing-source"]
    one_pps_config = timing_source_config["one-pps"]
    assert one_pps_config["gps-1pps"]["weighted-priority"] == 25


def test_set_config_frequency_GPS():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "timing-source": {
                    "frequency": {"gps": {"weighted-priority": 25}}
                }
            }
        }
    }
    configInst.set(input)
    # set_frequency_priority:
    # SyncE-BCM82398-100G-PIN1
    # SyncE-BCM82398-100G-PIN2
    # SyncE-BCM82780-10G
    # SyncE-BCM88470-10G
    # PTP-10MHz
    # GPS-10MHz  <======= No.6
    # SMA-10MHz
    # BITS
    configInst.timing_util.set_frequency_priority.assert_any_call("GPS-10MHz", 6)
    # set_frequency_priority_dpll3:
    # SyncE-BCM82398-100G-PIN1-DPLL3
    # SyncE-BCM82398-100G-PIN2-DPLL3
    # SyncE-BCM82780-10G-DPLL3
    # SyncE-BCM88470-10G-DPLL3
    # GPS-10MHz-DPLL3  <======== No.5
    # SMA-10MHz-DPLL3
    # BITS-DPLL3
    configInst.timing_util.set_frequency_priority_dpll3.assert_any_call(
        "GPS-10MHz-DPLL3", 5
    )

    configs = configInst.get()
    timing_source_config = configs["vyatta-system-v1:system"][
        "vyatta-system-timing-v1:timing"
    ]["timing-source"]
    frequency_config = timing_source_config["frequency"]
    assert frequency_config["gps"]["weighted-priority"] == 25


def test_set_config_wrong_parameters():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "wrong-parameters": {
                    "one-pps": {"gps-1pps": {"weighted-priority": 25}}
                }
            }
        }
    }
    configInst.set(input)
    configInst.timing_util.set_1pps_priority.assert_any_call("GPS-1PPS", 1)


def test_get_state_1pps():
    global g_timing_source_config
    stateInst = vyatta_system_timing.State()
    stateInst.timing_source_config = g_timing_source_config.copy()
    stateInst.timing_util = MagicMock()
    dpll1_status = {  # status from BSP api
        "current": "gps-1pps",
        "priority": ["gps-1pps", "ptp-1pps", "sma-1pps"],
        "status": {"dpll_lock": "Phase locked", "operating_status": "Free Run"},
    }
    dpll2_status = {  # status from BSP api
        "current": "SyncE-BCM82398-100G-PIN1",
        "priority": ["SyncE-BCM82398-100G-PIN1", "GPS-10MHz", "PTP-10MHz"],
        "status": {"dpll_lock": "Phase locked", "operating_status": "Free Run"},
    }
    stateInst.timing_util.get_dpll_status.side_effect = (
        lambda x: dpll1_status if x == 1 else dpll2_status
    )
    state = stateInst.get()
    assert (
        state["vyatta-system-v1:system"]["vyatta-system-timing-v1:timing"][
            "timing-status"
        ]["timing-source"]["one-pps-status"]["source"]
        == "gps-1pps"
    )
    assert (
        state["vyatta-system-v1:system"]["vyatta-system-timing-v1:timing"][
            "timing-status"
        ]["timing-source"]["frequency-status"]["source"]
        == "synce"
    )


def test_get_state_1pps_current_None():
    global g_timing_source_config
    stateInst = vyatta_system_timing.State()
    stateInst.timing_source_config = g_timing_source_config.copy()
    stateInst.timing_util = MagicMock()
    dpll1_status = {  # status from BSP api
        "current": "None",
        "priority": [],
        "status": {"operating_status": "Free Run"},
    }
    dpll2_status = {  # status from BSP api
        "current": "SyncE-BCM82398-100G-PIN1",
        "priority": ["SyncE-BCM82398-100G-PIN1", "GPS-10MHz", "PTP-10MHz"],
        "status": {"dpll_lock": "Phase locked", "operating_status": "Free Run"},
    }
    stateInst.timing_util.get_dpll_status.side_effect = (
        lambda x: dpll1_status if x == 1 else dpll2_status
    )
    state = stateInst.get()
    assert (
        state["vyatta-system-v1:system"]["vyatta-system-timing-v1:timing"][
            "timing-status"
        ]["timing-source"]["frequency-status"]["source"]
        == "synce"
    )
    assert (
        state["vyatta-system-v1:system"]["vyatta-system-timing-v1:timing"][
            "timing-status"
        ]["timing-source"]["one-pps-status"]["source"]
        == "None"
    )


def test_get_state_frequency_source_None():
    global g_timing_source_config
    stateInst = vyatta_system_timing.State()
    stateInst.timing_source_config = g_timing_source_config.copy()
    stateInst.timing_util = MagicMock()
    dpll1_status = {  # status from BSP api
        "current": "None",
        "priority": ["PTP-1PPS", "None", "None"],
        "status": {
            "dpll_lock": "Out of phase locked",
            "operating_status": "Pre-locked",
        },
    }
    dpll2_status = {  # status from BSP api
        "current": "None",
        "priority": ["PTP-10MHz", "SyncE-BCM88470-10G", "None"],
        "status": {"dpll_lock": "Phase locked", "operating_status": "Locked"},
    }
    stateInst.timing_util.get_dpll_status.side_effect = (
        lambda x: dpll1_status if x == 1 else dpll2_status
    )
    state = stateInst.get()
    assert (
        state["vyatta-system-v1:system"]["vyatta-system-timing-v1:timing"][
            "timing-status"
        ]["timing-source"]["frequency-status"]["source"]
        == "None"
    )

def test_set_config_tod_output_empty_param():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    configInst.cpld = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
            }
        }
    }
    configInst.set(input)
    configInst.cpld.set_tod_output.assert_any_call(0)

    configs = configInst.get()
    tod_output_config = configs["vyatta-system-v1:system"][
        "vyatta-system-timing-v1:timing"
    ]
    assert not tod_output_config['tod-output']

def test_set_config_tod_output_normal():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    configInst.cpld = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "tod-output": True
            }
        }
    }
    configInst.set(input)
    configInst.cpld.set_tod_output.assert_any_call(1)

    configs = configInst.get()
    tod_output_config = configs["vyatta-system-v1:system"][
        "vyatta-system-timing-v1:timing"
    ]
    assert tod_output_config["tod-output"] == True

def test_set_config_empty():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    configInst.cpld = MagicMock()
    input = {}
    configInst.set(input)
    configInst.cpld.set_tod_output.assert_any_call(0)

    configs = configInst.get()
    tod_output_config = configs["vyatta-system-v1:system"][
        "vyatta-system-timing-v1:timing"
    ]
    assert not tod_output_config['tod-output']

def test_check_config_1pps_same_priority():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "timing-source": {
                    "one-pps": {"gps-1pps": {"weighted-priority": 40}}
                }
            }
        }
    }
    errorFlag = False
    try:
        configInst.check(input)
    except Exception as e:
        print(f"{e}")
        errorFlag = True
        assert isinstance(e, vci.Exception)
    assert errorFlag == False

def test_check_config_frequency_same_priority():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "timing-source": {
                    "frequency": {"bits": {"weighted-priority": 20}}
                }
            }
        }
    }
    errorFlag = False
    try:
        configInst.check(input)
    except Exception as e:
        print(f"{e}")
        errorFlag = True
        assert isinstance(e, vci.Exception)
    assert errorFlag == False
