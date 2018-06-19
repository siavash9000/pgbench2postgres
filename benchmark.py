import os, string
import logging
import subprocess
import re
import time

#wait for postgres startup
time.sleep(25)

if os.environ.get('BENCHMARK_DB') is None:
    raise Exception('environment variable BENCHMARK_DB is not set')
if os.environ.get('RESULT_DB') is None:
    raise Exception('environment variable RESULT_DB is not set')

benchmark_database_name = os.environ.get('BENCHMARK_DB')
result_database_name = os.environ.get('RESULT_DB')


def create_db(db_name):
    check_database_exists_cmd = "psql -lqt | cut -d \| -f 1 | grep ${db_name}"
    check_database_exists_cmd = string.Template(check_database_exists_cmd).substitute(locals())
    check_database_exists_output = subprocess.getoutput(check_database_exists_cmd)
    logging.warning('OUTPUT:' + check_database_exists_output)
    if check_database_exists_output:
        logging.warning(string.Template("${db_name} exists: skipping").substitute(locals()))
    else:
        logging.warning(string.Template("${db_name} does not exists: creating").substitute(locals()))
        create_benchmark_db_cmd = string.Template("psql -c 'CREATE DATABASE ${db_name}'").substitute(locals())
        subprocess.getoutput(create_benchmark_db_cmd).strip()


def create_result_table():
    create_cmd = string.Template("psql -d results -c 'CREATE TABLE result(ID serial PRIMARY KEY NOT NULL, "
                                 "created_at TIMESTAMPTZ NOT NULL DEFAULT now(),error_count INT,"
                                 "latency_average REAL,tps_including_connections REAL, "
                                 "tps_excluding_connections REAL);'").substitute(locals())
    subprocess.getoutput(create_cmd).strip()


def pgbench_init(benchmark_db):
    logging.warning("starting pgbench init")
    pgbench_init = "pgbench -i -s 10 ${benchmark_db}"
    pgbench_init = string.Template(pgbench_init).substitute(locals())
    check_database_exists_output = subprocess.getoutput(pgbench_init).strip()
    subprocess.getoutput(check_database_exists_output).strip()


def run_pgbench(benchmark_db):
    logging.warning("starting pgbench run")
    benchmark_cmd = "pgbench -c 1 -j 1 -t 100 ${benchmark_db}"
    benchmark_cmd = string.Template(benchmark_cmd).substitute(locals())
    return subprocess.getoutput(benchmark_cmd).strip()


def parse_result(result):
    try:
        lines = result.split('\n')
        if 'WARNING:  corrupted statistics file' in result:
            logging.warning(lines[0])
            del lines[0]
        count = int(lines[7].split(':')[1].strip().split('/')[1])
        processed_count = int(lines[7].split(':')[1].strip().split('/')[0])
        error_count = processed_count - count
        latency_average = float(re.search('latency average = (.+?) ms', lines[8]).group(1))
        tps_including_connections = float(re.search('tps = (.+?) \(including connections establishing\)', lines[9]).group(1))
        tps_excluding_connections = float(re.search('tps = (.+?) \(excluding connections establishing\)', lines[10]).group(1))
        return error_count, latency_average, tps_including_connections, tps_excluding_connections
    except Exception as e:
        logging.exception(result)


def persist_result(error_count, latency_average, tps_including_connections, tps_excluding_connections):
    logging.warning("persisting result now")
    insert_cmd = string.Template("psql -d results -c '"
                                 "INSERT INTO result (error_count,latency_average,"
                                 "tps_including_connections,tps_excluding_connections) "
                                 "VALUES (${error_count}, ${latency_average}, "
                                 "${tps_including_connections}, "
                                 "${tps_excluding_connections});'").substitute(locals())
    subprocess.getoutput(insert_cmd).strip()

create_db(benchmark_database_name)
create_db(result_database_name)
create_result_table()
pgbench_init(benchmark_database_name)
while True:
    time.sleep(1)
    result = run_pgbench(benchmark_database_name)
    error_count, latency_average, tps_including_connections, tps_excluding_connections = parse_result(result)
    persist_result(error_count, latency_average, tps_including_connections, tps_excluding_connections)

