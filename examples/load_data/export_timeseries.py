#!/usr/bin/env python3
"""
Export timeseries data from Zont servers to local csv files.
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
import csv
from http.client import HTTPConnection

from zont_api import ZontAPI, ZontDevice, DATA_TYPES_Z3K

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(os.path.basename(__file__))

zont_api_log = logging.getLogger("zont_api")
zont_api_log.setLevel(logging.INFO)


class MetricStats:
    """
    Helper class to count unique metric series.
    """

    def __init__(self):
        self.empty = True
        self.oldest_ts = datetime.now().timestamp()
        self.newest_ts = 0
        self.stats = {}

    def __str__(self):
        if self.newest_ts > 0:
            return (
                f"{self.total_metrics()} metrics, {self.total_values()} values, "
                f"oldest @ {self.oldest_ts} {datetime.fromtimestamp(self.oldest_ts)}, "
                f"newest @ {self.newest_ts} {datetime.fromtimestamp(self.newest_ts)}"
            )
        return f"{self.total_metrics()} metrics, {self.total_values()} values"

    def update(self, metric_name, series_count, oldest_ts=None, newest_ts=None):
        """
        Update stats counters + range (optional).
        """
        self.empty = False

        if oldest_ts is not None:
            self.oldest_ts = min(self.oldest_ts, oldest_ts)

        if newest_ts is not None:
            self.newest_ts = max(self.newest_ts, newest_ts)

        if metric_name not in self.stats:
            self.stats[metric_name] = series_count
            return
        self.stats[metric_name] += series_count

    def total_metrics(self):
        """
        Get total number of unique metric names.
        """
        return len(self.stats.keys())

    def total_values(self):
        """
        Get total sum of all values (metric series).
        """
        values = 0
        for _, series_count in self.stats.items():
            values += series_count
        return values


global_stats = MetricStats()


def save_csv(metric_name, arr, targetdir="."):
    """
    Create csv file out of timeseries array for a given metric.
    """
    result = []

    for e in arr:
        result.append({"timestamp": e[0], metric_name: e[1]})

    output_file = f"{targetdir}/{metric_name}.csv"
    logger.debug(
        "saving %d entries for %s to %s", len(result), metric_name, output_file
    )

    os.makedirs(targetdir, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as csvout:
        fieldnames = ["timestamp", metric_name]
        writer = csv.DictWriter(csvout, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(result)


def datetime_str_to_ts(datetime_str: str):
    """
    Convert datetime string to UNIX timestamp.
    """
    for format_str in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(datetime_str, format_str)
        except ValueError:
            continue
    raise ValueError(f'could not get timestamp from "{datetime_str}"')


def export_data(
    dt_from: datetime, dt_to: datetime, zapi: ZontAPI, device: ZontDevice, args
):
    """
    Fetch timeseries data for a given device, do all required conversions,
    and save csv file for every exported metric series.
    """
    iteration_stats = MetricStats()

    targetdir = args.targetdir
    if args.period == "hourly":
        targetdir = dt_from.strftime(f"{args.targetdir}/%Y/%Y-%m/%Y-%m-%d/%H")
    elif args.period == "daily":
        targetdir = dt_from.strftime(f"{args.targetdir}/%Y/%Y-%m/%Y-%m-%d")

    interval = (dt_from.timestamp(), dt_to.timestamp())
    data = zapi.load_data(device.id, data_types=DATA_TYPES_Z3K, interval=interval)

    # analog inputs like power controller
    # for analog_input in device.get_analog_inputs():
    #    analog_input_id = str(analog_input.get("id"))
    for analog_input_id in data.get("z3k_analog_input").keys():
        subtree = data.get("z3k_analog_input").get(analog_input_id, {})
        for k, v in subtree.items():
            if len(v) == 0:
                continue
            metric = f"device_{device.id}.analog_input_{analog_input_id}.{k}"
            timeseries = zapi.convert_delta_time_array(
                subtree.get(k), filter_duplicates=args.filter_duplicates
            )
            global_stats.update(
                metric,
                len(timeseries),
                oldest_ts=timeseries[0][0],
                newest_ts=timeseries[-1][0],
            )
            iteration_stats.update(metric, len(timeseries))
            save_csv(metric, timeseries, targetdir=targetdir)

    # analog temperature sensors (wired)
    # for analog_temperature_sensor in device.get_analog_temperature_sensors():
    #    analog_temperature_sensor_id = str(analog_temperature_sensor.get("id"))
    for analog_temperature_sensor_id in data.get("z3k_temperature").keys():
        dta = data.get("z3k_temperature").get(analog_temperature_sensor_id, [])
        if len(dta) == 0:
            continue
        metric = f"device_{device.id}.analog_temperature_sensor_{analog_temperature_sensor_id}"
        timeseries = zapi.convert_delta_time_array(
            dta, filter_duplicates=args.filter_duplicates
        )
        global_stats.update(
            metric,
            len(timeseries),
            oldest_ts=timeseries[0][0],
            newest_ts=timeseries[-1][0],
        )
        iteration_stats.update(metric, len(timeseries))
        save_csv(metric, timeseries, targetdir=targetdir)

    # boiler adapters
    # for boiler_adapter in device.get_boiler_adapters():
    #    boiler_adapter_id = str(boiler_adapter.get("id"))
    for boiler_adapter_id in data.get("z3k_boiler_adapter").keys():
        subtree = data.get("z3k_boiler_adapter").get(boiler_adapter_id, {})
        for k, v in subtree.items():
            # if k == "s":
            #    continue
            if len(v) == 0:
                continue
            metric = f"device_{device.id}.boiler_adapter_{boiler_adapter_id}.{k}"
            timeseries = zapi.convert_delta_time_array(
                subtree.get(k), filter_duplicates=args.filter_duplicates
            )
            global_stats.update(
                metric,
                len(timeseries),
                oldest_ts=timeseries[0][0],
                newest_ts=timeseries[-1][0],
            )
            iteration_stats.update(metric, len(timeseries))
            save_csv(metric, timeseries, targetdir=targetdir)

    # heating circuits
    # for heating_circuit in device.get_heating_circuits():
    #    heating_circuit_id = str(heating_circuit.get("id"))
    for heating_circuit_id in data.get("z3k_heating_circuit").keys():
        subtree = data.get("z3k_heating_circuit").get(heating_circuit_id, {})
        for k, v in subtree.items():
            if len(v) == 0:
                continue
            metric = f"device_{device.id}.heating_circuit_{heating_circuit_id}.{k}"
            timeseries = zapi.convert_delta_time_array(
                subtree.get(k), filter_duplicates=args.filter_duplicates
            )
            global_stats.update(
                metric,
                len(timeseries),
                oldest_ts=timeseries[0][0],
                newest_ts=timeseries[-1][0],
            )
            iteration_stats.update(metric, len(timeseries))
            save_csv(metric, timeseries, targetdir=targetdir)

    logger.info(
        "range %s to %s (period=%s): %s",
        dt_from,
        dt_to,
        args.period,
        iteration_stats,
    )

    return 0


def main():
    """
    Entrypoint.
    """
    parser = argparse.ArgumentParser(
        description="Export timeseries data from Zont servers to local csv files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--from",
        type=str,
        dest="from_datetime",
        required=True,
        help="starting timestamp",
    )
    parser.add_argument(
        "--to", type=str, dest="to_datetime", required=True, help="snding timestamp"
    )
    parser.add_argument(
        "--exclusive-to",
        action="store_true",
        default=True,
        help="exclude 1 second from ending timestamp",
    )
    parser.add_argument(
        "--period",
        type=str,
        default=None,
        choices=("hourly", "daily"),
        help="split output to periods (dedicated directories will be created under TARGETDIR)",
    )
    parser.add_argument(
        "--filter-duplicates",
        action="store_true",
        default=False,
        help="filter duplicate datapoints",
    )
    parser.add_argument(
        "--targetdir",
        type=str,
        default="data",
        help="target directory for exported data",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="enable extra debugging output",
    )
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        zont_api_log.setLevel(logging.DEBUG)
        urllib3_log = logging.getLogger("urllib3")
        urllib3_log.setLevel(logging.DEBUG)
        HTTPConnection.debuglevel = 1

    dt_from = datetime_str_to_ts(args.from_datetime)
    dt_to = datetime_str_to_ts(args.to_datetime)
    dt_delta = dt_to - dt_from
    if args.exclusive_to:
        dt_to -= timedelta(seconds=1)

    logger.info(
        "started with dt_from=%s, dt_to=%s, dt_delta=%s",
        dt_from,
        dt_to,
        dt_delta,
    )

    zapi = ZontAPI()
    devices = zapi.get_devices()
    device = devices[0]

    if args.period is None:
        export_data(dt_from, dt_to, zapi, device, args)

    elif args.period == "hourly":
        if dt_delta < timedelta(hours=1):
            raise ValueError(
                f"can not split to hours as dt_delta < 1 hour ({dt_delta})"
            )

        dt_ifrom = dt_from
        while True:
            dt_ito = dt_ifrom + timedelta(hours=1) - timedelta(seconds=1)
            export_data(dt_ifrom, dt_ito, zapi, device, args)
            dt_ifrom = dt_ito + timedelta(seconds=1)
            dt_ito = dt_ifrom + timedelta(hours=1) - timedelta(seconds=1)
            if dt_ito > dt_to:
                break

    elif args.period == "daily":
        if dt_delta < timedelta(hours=24):
            raise ValueError(
                f"can not split to days as dt_delta < 24 hours ({dt_delta})"
            )

        dt_ifrom = dt_from
        while True:
            dt_ito = dt_ifrom + timedelta(hours=24) - timedelta(seconds=1)
            export_data(dt_ifrom, dt_ito, zapi, device, args)
            dt_ifrom = dt_ito + timedelta(seconds=1)
            dt_ito = dt_ifrom + timedelta(hours=24) - timedelta(seconds=1)
            if dt_ito > dt_to:
                break

    if not global_stats.empty:
        logger.info("========[ summary of collected metrics follows ]========")
        for k, v in iter(sorted(global_stats.stats.items())):
            logger.info("%s: %d", k, v)
        logger.info("========[ %s ]========", global_stats)
    else:
        logger.info("no timeseries collected for a given period")

    logger.info("stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
