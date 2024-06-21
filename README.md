# prom2csv: Export prometheus metrics into CSV

[![PyPI - Version](https://img.shields.io/pypi/v/prom2csv)](https://pypi.org/project/prom2csv/)
[![License](https://img.shields.io/pypi/l/prom2csv)](https://raw.githubusercontent.com/pierresouchay/prom2csv/main/LICENSE)

A hi-performance tool to export prometheus metrics in a CSV file.

It will help you fetching the last value of metrics extracted from prometheus, including computed
values and export those results as CSV files. Which make it efficient to export those data to other
tools.

It also supports generating IDs based on labels of metrics (see `--row-id-expression`), so tools
can compare values or override existing ones easily => one metric is always named the same way.

## Install / Requirements

You can install it on any system supporting python 3.9+, it's only requirement is `requests`.

```bash
pip install prom2csv
```

You can then run it with `prom2csv` in the terminal.

## Usage
```
usage: prom2csv [-h] [--prometheus-url PROMETHEUS_URL] [--column-name-mapping COLUMN_NAME_MAPPING COLUMN_NAME_MAPPING]
                [--row-id-expression ROW_ID_EXPRESSION] [--remove-column REMOVE_COLUMN] [--skip-csv-header] [-o OUTPUT_CSV] [-v]
                query

Export Prometheus time-serie to CSV

positional arguments:
  query                 Prometheus query to perform

options:
  -h, --help            show this help message and exit
  --prometheus-url PROMETHEUS_URL
                        Connect to the given prometheus host (default=$PROMETHEUS_URL or http://localhost:9090)
  --column-name-mapping COLUMN_NAME_MAPPING COLUMN_NAME_MAPPING
                        map a column into a specific name (id, timestamp, value + labels) into another name: --column-name-mapping id my_id (can be
                        repeated)
  --row-id-expression ROW_ID_EXPRESSION
                        First column value (default=__name__'). You can use python expression using labels: --name 'f"{__name__}.{__job__}"
  --remove-column REMOVE_COLUMN
                        Remove a column, can be specified multiple times
  --skip-csv-header     Do not create CSV header
  -o OUTPUT_CSV, --output-csv OUTPUT_CSV
                        File to perform the output to, defaults to stdout
  -v, --version         show program's version number and exit
```

# Examples

## Get the size of the table user on all Postgresql instance in env=prod

```
./prom2csv.py 'pg_stat_user_tables_n_live_tup{relname="user",env="prod"}'    
id,timestamp,value,datname,duty,env,hostname,instance,job,relname,schemaname,tenant_id,type
pg_stat_user_tables_n_live_tup,2024-06-05 09:54:09.274000+00:00,180,pgdb,always,prod,prod1005-01,prod1005-01.example.org:39187,postgres,user,public,1005,app
pg_stat_user_tables_n_live_tup,2024-06-05 09:54:09.274000+00:00,107,pgdb,always,prod,prod1006-01,prod1006-01.example.org:39187,postgres,user,public,1006,app
```

### Same, but set the name of instance as first row and hide some rows

```bash
./prom2csv.py 'pg_stat_user_tables_n_live_tup{relname="user",env="prod"}' \
  --column-name-mapping id my_instance \
  --row-id-expression 'instance' \
  --column-name-mapping tenant_id my_customer \
  --remove-column timestamp \
  --remove-column type \
  --remove-column duty
my_instance,value,datname,env,hostname,instance,job,relname,schemaname,my_customer
prod1005-01.example.org:39187,180,pgdb,prod,prod1005-01,prod1005-01.example.org:39187,postgres,user,public,1005
prod1006-01.example.org:39187,107,pgdb,prod,prod1006-01,prod1006-01.example.org:39187,postgres,user,public,1006
```

## List all machines/partitions in dev or prod with partition usage > 50%

```
./prom2csv.py --column-name-mapping id instance --row-id-expression 'instance' '(node_filesystem_free_bytes{env=~"dev|prod",device!~"rootfs",fstype!="tmpfs"} / node_filesystem_size_bytes{env=~"dev|prod",device!~"rootfs",fstype!="tmpfs"}) < 0.5'
```
