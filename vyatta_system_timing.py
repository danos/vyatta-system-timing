#!/usr/bin/python3
#
# Copyright (c) 2021, AT&T Intellectual Property.  All Rights Reserved
#
# SPDX-License-Identifier: LGPL-2.1-only

import vci
import timing_utility
import json
from threading import Lock

timing_source_config = {
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
default_timing_source_config = timing_source_config.copy()


def src_name_from_dpll1(dpll1_name):
    return dpll1_name  # same to name from command line


def src_name_from_dpll2(dpll2_name):
    dpll2_to_src_name = {
        "GPS-10MHz": "GPS",
        "SyncE-BCM82398-100G-PIN1": "SYNCE",
        "SyncE-BCM82398-100G-PIN2": "SYNCE",
        "SyncE-BCM82780-10G": "SYNCE",
        "SyncE-BCM88470-10G": "SYNCE",
        "PTP-10MHz": "PTP",
        "SMA-10MHz": "SMA",
        "BITS": "BITS",
    }
    if dpll2_name not in dpll2_to_src_name:
        return "None"
    return dpll2_to_src_name[dpll2_name]


def sorted_by_weighted_priority(items):
    return sorted(items, key=lambda item: item["weighted-priority"], reverse=True)


class Config(vci.Config):
    def __init__(self, *args, **kwargs):
        global timing_source_config
        super().__init__(*args, **kwargs)
        self.timing_util = timing_utility.TimingUtility()
        self.timing_source_config = timing_source_config
        self.mutex = Lock()
        # config_file_path = '/etc/vyatta/vyatta-system-timing.json'

    def set_config(self, cmd_dict, cmd_type):
        """set config into self.timing_source_config

        Args:
            cmd_dict (dict): command data structure
            cmd_type (string): command type, like one-pps, frequency
        """
        for item in cmd_dict[cmd_type]:
            src_type = item["source"]
            weighted_priority = item["weighted-priority"]
            for saved_item in self.timing_source_config[cmd_type]:
                if saved_item["source"] == src_type:
                    saved_item["weighted-priority"] = weighted_priority

    def set(self, input):
        """set function of Config class

        Args:
            input (dict):dictionary from vci core, example of input:
                {'vyatta-system-v1:system':
                    {'vyatta-system-timing-v1:timing':
                        {'timing-source':
                            {'one-pps':
                                [{'one-pps-src': 'GPS-1PPS',
                                  'weighted-priority': 20}]
                            }
                        }
                    }
                }
        """
        print(f"set config {input}", flush=True)
        # do something to realize the configuration on the system
        self.mutex.acquire()
        cmd_dict = default_timing_source_config
        try:
            cmd_dict = input["vyatta-system-v1:system"][
                "vyatta-system-timing-v1:timing"
            ]["timing-source"]
        except:
            if bool(input):  # dictionary is not empty
                print(f"wrong params for set: {input}", flush=True)
                self.mutex.release()
                return
        if "one-pps" in cmd_dict:
            self.set_config(
                cmd_dict, "one-pps"
            )  # save config into self.timing_source_config
            # sort self.timing_source_config
            self.timing_source_config["one-pps"] = sorted_by_weighted_priority(
                self.timing_source_config["one-pps"]
            )
            # let's config all 1PPS items to BSP, to avoid priority order issue.
            for i in range(len(self.timing_source_config["one-pps"])):
                src_name = self.timing_source_config["one-pps"][i]["source"]
                real_priority = 1 + i  # priority starts from 1
                print(f"set_1pps_priority:{src_name}, {real_priority}")
                self.timing_util.set_1pps_priority(src_name, real_priority)
        if "frequency" in cmd_dict:
            self.set_config(
                cmd_dict, "frequency"
            )  # save config into self.timing_source_config
            # sort self.timing_source_config
            self.timing_source_config["frequency"] = sorted_by_weighted_priority(
                self.timing_source_config["frequency"]
            )
            # config to BSP, since we might have 1->n configurations to BSP,
            # let's config all frequency items to BSP,
            # to avoid priority order issue.
            real_priority = 0
            real_priority3 = 0  # for dpll3 specifically
            for i in range(len(self.timing_source_config["frequency"])):
                src_name = self.timing_source_config["frequency"][i]["source"]
                if src_name in ["GPS", "SMA", "PTP"]:
                    real_priority += 1
                    print(
                        f"set_frequency_priority:{src_name}-10MHz, {real_priority}",
                        flush=True,
                    )
                    self.timing_util.set_frequency_priority(
                        f"{src_name}-10MHz", real_priority
                    )
                    if src_name != "PTP":  # no DPLL3 configuration for PTP
                        real_priority3 += 1  # for dpll3 specifically
                        print(
                            f"set_frequency_priority_dpll3:{src_name}-10MHz-DPLL3, {real_priority3}",
                            flush=True,
                        )
                        self.timing_util.set_frequency_priority_dpll3(
                            f"{src_name}-10MHz-DPLL3", real_priority3
                        )
                elif src_name == "BITS":
                    real_priority += 1
                    print(f"set_frequency_priority: BITS, {real_priority}", flush=True)
                    self.timing_util.set_frequency_priority("BITS", real_priority)
                    real_priority3 += 1  # for dpll3 specifically
                    print(
                        f"set_frequency_priority_dpll3: BITS-DPLL3, {real_priority3}",
                        flush=True,
                    )
                    self.timing_util.set_frequency_priority_dpll3(
                        "BITS-DPLL3", real_priority3
                    )
                elif src_name == "SYNCE":
                    for target_name in [
                        "SyncE-BCM82398-100G-PIN1",
                        "SyncE-BCM82398-100G-PIN2",
                        "SyncE-BCM82780-10G",
                        "SyncE-BCM88470-10G",
                    ]:
                        real_priority += 1
                        print(
                            f"set_frequency_priority: {target_name}, {real_priority}",
                            flush=True,
                        )
                        self.timing_util.set_frequency_priority(
                            target_name, real_priority
                        )
                        real_priority3 += 1  # for dpll3 specifically
                        print(
                            f"set_frequency_priority_dpll3: {target_name}, {real_priority3}",
                            flush=True,
                        )
                        self.timing_util.set_frequency_priority_dpll3(
                            target_name + "-DPLL3", real_priority3
                        )
        self.mutex.release()
        return

    def get(self):
        """get function for Config class

        Returns:
            dict format same to input of set() function
        """
        # return the configuration
        print("get config", flush=True)
        return {
            "vyatta-system-v1:system": {
                "vyatta-system-timing-v1:timing": {
                    "timing-source": self.timing_source_config
                }
            }
        }

    def check(self, input):
        """check config

        Args:
            input (dict):dictionary from vci core, example of input:
                {'vyatta-system-v1:system':
                    {'vyatta-system-timing-v1:timing':
                        {'timing-source':
                            {'one-pps':
                                [{'one-pps-src': 'GPS-1PPS',
                                  'weighted-priority': 20}]
                            }
                        }
                    }
                }
        """
        # do an additional configuration checks
        print(f"check config {input}", flush=True)
        return


class State(vci.State):
    def __init__(self, *args, **kwargs):
        global timing_source_config
        super().__init__(*args, **kwargs)
        self.timing_util = timing_utility.TimingUtility()
        self.timing_source_config = timing_source_config

    def get(self):
        """Get state of timing source

        Returns:
            dict: 1PPS and frequence timing source state
        """
        # do something to retrieve the state of the feature
        print("get State", flush=True)
        status1 = self.timing_util.get_dpll_status(1)
        status2 = self.timing_util.get_dpll_status(2)
        print(f"status1:{status1} status2:{status2}")
        one_pps_status = {
            "source": src_name_from_dpll1(status1["current"]),
            "priority": [
                f"weighted_priority:{item['weighted-priority']}, source:{item['source']}"
                for item in self.timing_source_config["one-pps"]
            ],
            "operating-status": status1["status"]["operating_status"],
        }
        print(f"one-pps status:{one_pps_status}", flush=True)
        frequency_status = {
            "source": src_name_from_dpll2(status2["current"]),
            "priority": [
                f"weighted_priority:{item['weighted-priority']}, source:{item['source']}"
                for item in self.timing_source_config["frequency"]
            ],
            "operating-status": status2["status"]["operating_status"],
        }
        print(f"frequency status:{frequency_status}", flush=True)
        state = {
            "vyatta-system-v1:system": {
                "vyatta-system-timing-v1:timing": {
                    "timing-status": {
                        "timing-source": {
                            "one-pps-status": one_pps_status,
                            "frequency-status": frequency_status,
                        }
                    }
                }
            }
        }
        return state


if __name__ == "__main__":
    (
        vci.Component("net.vyatta.vci.system.timing")
        .model(
            vci.Model("net.vyatta.vci.system.timing.v1").config(Config()).state(State())
        )
        .run()
        .wait()
    )
