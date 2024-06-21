#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import os
import sys
from typing import Any, Iterable, TextIO

import requests

__version__ = "0.9.1"


class CSVParams:
    def __init__(
        self,
        skip_csv_header: bool,
        column_mappings: dict[str, str],
        removed_columns: set[str],
        labelnames: list[str],
        evaluation: str,
    ) -> None:
        self.skip_csv_header = skip_csv_header
        self.column_mappings = column_mappings
        self.removed_columns = removed_columns
        self.labelnames = labelnames
        self.evaluation = evaluation


def write_csv_on_stream(
    stream: TextIO, params: CSVParams, results: Iterable[dict[str, Any]]
) -> None:
    writer = csv.writer(stream)
    # Write the header
    if params.skip_csv_header is False:
        writer.writerow(
            [
                params.column_mappings.get(col, col)
                for col in ["id", "timestamp", "value"] + params.labelnames
                if col not in params.removed_columns
            ]
        )

    for result in results:
        try:
            line = []
            if "id" not in params.removed_columns:
                line.append(eval(params.evaluation, None, result["metric"]))
            if "timestamp" not in params.removed_columns:
                line.append(
                    dt.datetime.fromtimestamp(result["value"][0], tz=dt.timezone.utc)
                )
            if "value" not in params.removed_columns:
                line.append(result["value"][1])
            for label in params.labelnames:
                if label not in params.removed_columns:
                    line.append(result["metric"].get(label, ""))
            writer.writerow(line)
        except NameError as err:
            print(
                f"{err}: Failed building ID using {params.evaluation}, possible keys:",
                "\n * ".join(sorted(result["metric"].keys())),
                file=sys.stderr,
            )
            raise


def write_results_in_csv(
    output_csv: str, params: CSVParams, results: Iterable[dict[str, Any]]
) -> None:
    stream = sys.stdout

    def flush_stdout(out: TextIO) -> None:
        out.flush()

    on_stream_end = flush_stdout
    if output_csv and output_csv != "-":
        stream = open(output_csv, "wt", encoding="utf8")

        def close_file(out: TextIO) -> None:
            out.close()

        on_stream_end = close_file

    try:
        write_csv_on_stream(stream=stream, params=params, results=results)
    finally:
        on_stream_end(stream)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Prometheus time-serie to CSV")
    parser.add_argument(
        "--prometheus-url",
        default=os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
        help="Connect to the given prometheus host (default=$PROMETHEUS_URL or http://localhost:9090)",
    )
    parser.add_argument(
        "--column-name-mapping",
        action="append",
        nargs=2,
        help=(
            "map a column into a specific name (id, timestamp, value + labels) into another name:"
            " --column-name-mapping id my_id (can be repeated)"
        ),
    )
    parser.add_argument(
        "--row-id-expression",
        default="__name__",
        help=(
            "First column value (default=__name__'). "
            'You can use python expression using labels: --name \'f"{__name__}.{__job__}"'
        ),
    )
    parser.add_argument(
        "--remove-column",
        action="append",
        help="Remove a column, can be specified multiple times",
    )
    parser.add_argument(
        "--skip-csv-header",
        default=False,
        action="store_true",
        help="Do not create CSV header",
    )
    parser.add_argument(
        "-o",
        "--output-csv",
        default="-",
        help="File to perform the output to, defaults to stdout",
    )
    parser.add_argument("query", nargs=1, help="Prometheus query to perform")
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )
    ns = parser.parse_args()

    column_mappings: dict[str, str] = (
        {elem[0]: elem[1] for elem in ns.column_name_mapping}
        if ns.column_name_mapping
        else {}
    )
    removed_columns = set(ns.remove_column) if ns.remove_column else set()

    response = requests.get(
        f"{ns.prometheus_url}/api/v1/query", params={"query": ns.query}
    )
    results = response.json()["data"]["result"]

    # Build a list of all labelnames used.
    labelnames_set: set[str] = set()
    for result in results:
        labelnames_set.update(result["metric"].keys())

    # Canonicalize
    has_name_prop = "__name__" in labelnames_set
    if has_name_prop:
        labelnames_set.discard("__name__")
    evaluation: str = ns.row_id_expression
    if evaluation == "__name__" and not has_name_prop:
        removed_columns.add("id")
    labelnames = list(sorted(labelnames_set))
    params = CSVParams(
        skip_csv_header=ns.skip_csv_header,
        column_mappings=column_mappings,
        removed_columns=removed_columns,
        labelnames=labelnames,
        evaluation=evaluation,
    )
    write_results_in_csv(output_csv=ns.output_csv, params=params, results=results)


if __name__ == "__main__":
    main()
