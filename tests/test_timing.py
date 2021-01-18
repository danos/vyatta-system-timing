#!/usr/bin/env python3
#
# Copyright (c) 2021, AT&T Intellectual Property.  All Rights Reserved
#
# SPDX-License-Identifier: LGPL-2.1-only

"""
Unit-tests for the vyatta_system_timing.py module.
"""
from os.path import dirname, realpath, sep, pardir
import sys, os

root = os.path.join(dirname(realpath(__file__)), "../")
sys.path.append(root)

from unittest.mock import MagicMock, Mock
import pytest
import vyatta_system_timing

g_timing_source_config = {
    "one-pps": [
        {"source": "GPS-1PPS", "weighted-priority": 50},
        {"source": "PTP-1PPS", "weighted-priority": 40},
        {"source": "SMA-1PPS", "weighted-priority": 30},
        {"source": "ToD-1PPS", "weighted-priority": 20},
    ],
    "frequency": [
        {"source": "GPS", "weighted-priority": 50},
        {"source": "SYNCE", "weighted-priority": 40},
        {"source": "PTP", "weighted-priority": 30},
        {"source": "SMA", "weighted-priority": 20},
        {"source": "BITS", "weighted-priority": 10},
    ],
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
                    "one-pps": [{"source": "GPS-1PPS", "weighted-priority": 25}]
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
    assert one_pps_config[2]["source"] == "GPS-1PPS"
    assert one_pps_config[2]["weighted-priority"] == 25


def test_set_config_frequency_GPS():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "timing-source": {
                    "frequency": [{"source": "GPS", "weighted-priority": 25}]
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
    one_pps_config = timing_source_config["frequency"]
    assert one_pps_config[2]["source"] == "GPS"
    assert one_pps_config[2]["weighted-priority"] == 25


def test_set_config_wrong_parameters():
    global g_timing_source_config
    configInst = vyatta_system_timing.Config()
    configInst.timing_source_config = g_timing_source_config.copy()
    configInst.timing_util = MagicMock()
    input = {
        "vyatta-system-v1:system": {
            "vyatta-system-timing-v1:timing": {
                "wrong-parameters": {
                    "one-pps": [{"source": "GPS-1PPS", "weighted-priority": 25}]
                }
            }
        }
    }
    configInst.set(input)
    configInst.timing_util.set_1pps_priority.assert_not_called()


def test_get_state_1pps():
    global g_timing_source_config
    stateInst = vyatta_system_timing.State()
    stateInst.timing_source_config = g_timing_source_config.copy()
    stateInst.timing_util = MagicMock()
    dpll1_status = {  # status from BSP api
        "current": "GPS-1PPS",
        "priority": ["GPS-1PPS", "PTP-1PPS", "SMA-1PPS"],
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
        == "GPS-1PPS"
    )
    assert (
        state["vyatta-system-v1:system"]["vyatta-system-timing-v1:timing"][
            "timing-status"
        ]["timing-source"]["frequency-status"]["source"]
        == "SYNCE"
    )


def test_get_state_1pps_current_None():
    """
    one-pps status:{'source': 'None', 'priority': ['weighted_priority:50, source:GPS-1PPS', 'weighted_priority:40, source:PT
    P-1PPS', 'weighted_priority:30, source:SMA-1PPS', 'weighted_priority:20, source:ToD-1PPS'], 'operating-status': 'Free Run'}
    """
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
        == "SYNCE"
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