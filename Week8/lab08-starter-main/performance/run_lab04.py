"""Run Lab 4 on isolated temporary SQLite databases and export HTML/CSV/logs."""
import argparse
import csv
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
CASES = {"A": (10, 2, "30s"), "B": (50, 5, "60s"), "C": (200, 50, "30s")}
SERVER = """
import logging, sys, threading
from app import create_app
from models import Book, db
from werkzeug.serving import make_server
logging.getLogger('werkzeug').setLevel(logging.WARNING)
app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + sys.argv[1],
    'SQLALCHEMY_ENGINE_OPTIONS': {'pool_size': int(sys.argv[3]), 'max_overflow': 0, 'pool_timeout': 5}})
with app.app_context():
    db.session.add_all([Book(title=f'Seed {i}', author='locust', year=(1996,2017,2021)[i%3]) for i in range(50)])
    db.session.commit()
    print(type(db.engine.pool).__name__, db.engine.pool.status(), flush=True)
httpd = make_server('127.0.0.1', int(sys.argv[2]), app, threaded=True)
def stop():
    sys.stdin.readline()
    httpd.shutdown()
threading.Thread(target=stop, daemon=True).start()
try:
    httpd.serve_forever()
finally:
    httpd.server_close()
    with app.app_context():
        db.session.remove()
        db.engine.dispose()
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', nargs='+', choices=CASES, default=list(CASES))
    parser.add_argument('--port', type=int, default=5054)
    parser.add_argument('--pool-size', type=int, default=15)
    parser.add_argument('--suffix', default='')
    parser.add_argument('--failure-rate', type=float, default=0.01)
    args = parser.parse_args()
    if args.pool_size < 1 or not 0 <= args.failure_rate <= 1:
        parser.error('pool-size must be positive; failure-rate must be between 0 and 1')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.suffix):
        parser.error('suffix may contain only letters, digits, hyphens and underscores')
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    host = f'http://127.0.0.1:{args.port}'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', args.port))
    summary = reports / f'lab04-summary{args.suffix}.json'
    results = json.loads(summary.read_text(encoding='utf-8')) if summary.exists() else []
    results = [r for r in results if r['case'] not in [c + args.suffix for c in args.cases]]
    for case in args.cases:
        users, rate, duration = CASES[case]
        name = case + args.suffix
        print(f'{name}: {users} users, {rate}/s, {duration}, pool={args.pool_size}', flush=True)
        with tempfile.TemporaryDirectory(prefix='lab04-', dir=reports) as temp:
            database = (Path(temp) / 'books.db').resolve().as_posix()
            with (reports / f'{name}-server.log').open('w', encoding='utf-8') as log:
                server = subprocess.Popen(
                    [sys.executable, '-u', '-c', SERVER, database, str(args.port), str(args.pool_size)],
                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                )
                try:
                    for _ in range(100):
                        if server.poll() is not None:
                            raise RuntimeError(f'Server stopped: see {name}-server.log')
                        try:
                            with urlopen(host + '/health', timeout=1) as response:
                                if response.status == 200:
                                    break
                        except (URLError, TimeoutError):
                            time.sleep(0.2)
                    else:
                        raise RuntimeError('API did not become ready')
                    command = [sys.executable, '-m', 'locust', '-f', 'performance/locustfile.py',
                               '--headless', '-H', host, '-u', str(users), '-r', str(rate),
                               '-t', duration, '--stop-timeout', '5', '--only-summary',
                               '--html', f'reports/{name}.html', '--csv', f'reports/{name}']
                    env = dict(os.environ, LOCUST_SIMULATED_FAILURE_RATE=str(args.failure_rate))
                    with (reports / f'{name}-locust.log').open('w', encoding='utf-8') as output:
                        run = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
                    with (reports / f'{name}_stats.csv').open(encoding='utf-8-sig', newline='') as f:
                        total = next(r for r in csv.DictReader(f) if r['Name'] == 'Aggregated')
                    count, failures = int(total['Request Count']), int(total['Failure Count'])
                    result = dict(case=name, users=users, spawn_rate=rate, duration=duration,
                                  pool_size=args.pool_size, injection_probability=args.failure_rate,
                                  requests=count, failures=failures, p95_ms=float(total['95%']),
                                  failure_rate=failures / count if count else None,
                                  rps=float(total['Requests/s']), exit_code=run.returncode)
                    results.append(result)
                    summary.write_text(
                        json.dumps(results, indent=2) + '\n', encoding='utf-8')
                    print(json.dumps(result), flush=True)
                    if run.returncode not in (0, 1) or not count:
                        raise RuntimeError(f'Locust did not complete: see {name}-locust.log')
                finally:
                    try:
                        server.communicate('stop\n', timeout=10)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait()


if __name__ == '__main__':
    main()
