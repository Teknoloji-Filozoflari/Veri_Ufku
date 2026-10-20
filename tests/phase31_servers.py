"""Real disposable TLS HTTP and PostgreSQL; no user data or ambient secrets."""

import json
import os
import socket
import ssl
import subprocess
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def tls_files(root):
    root = Path(root)
    cert, key = root / "server.crt", root / "server.key"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    key.chmod(0o600)
    return cert, key


@contextmanager
def api_server(root):
    cert, key = tls_files(root)
    calls = []
    state = dict(mode="normal", retries=0)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            calls.append((self.command, self.path))
            mode = state["mode"]
            if mode == "slow":
                time.sleep(3)
            if mode == "redirect":
                self.send_response(302)
                self.send_header("Location", "/data")
                self.end_headers()
                return
            if (
                mode == "auth"
                and self.headers.get("Authorization")
                != "Bearer fixture-secret-never-log"
            ):
                self.send_response(401)
                self.end_headers()
                return
            if mode == "retry" and state["retries"] == 0:
                state["retries"] += 1
                self.send_response(429)
                self.send_header("Retry-After", "0")
                self.end_headers()
                return
            second = self.path.startswith("/page2")
            rows = (
                [dict(id=3, amount=30)]
                if second
                else [dict(id=1, amount=10), dict(id=2, amount=20)]
            )
            if mode == "duplicate" and second:
                rows[0]["id"] = 2
            next_url = None if second else "/page2"
            if mode == "loop":
                next_url = "/data"
            if mode == "external":
                next_url = "https://another.invalid/data"
            payload = dict(items=rows, next=next_url, total=4 if mode == "gap" else 3)
            if mode == "unknown":
                payload.pop("total")
            if mode == "missing_next":
                payload.pop("next")
            raw = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header(
                "X-Snapshot-ID",
                "changed" if mode == "mutation" and second else "snapshot-1",
            )
            self.send_header("ETag", '"page2"' if second else '"page1"')
            self.end_headers()
            try:
                self.wfile.write(raw)
            except OSError:
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield dict(
            endpoint=f"https://localhost:{server.server_port}/data",
            ca_file=str(cert),
            state=state,
            calls=calls,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@contextmanager
def postgres_server(root, binaries):
    import psycopg

    root, binaries = Path(root), Path(binaries)
    cert, key = tls_files(root)
    data = root / "pgdata"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(binaries.parent / "lib")
    subprocess.run(
        [
            str(binaries / "initdb"),
            "-D",
            str(data),
            "--auth=trust",
            "--no-locale",
            "-E",
            "UTF8",
        ],
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with (data / "postgresql.conf").open("a") as stream:
        stream.write(
            f"\nlisten_addresses='127.0.0.1'\nport={port}\nunix_socket_directories='{root}'\nssl=on\nssl_cert_file='{cert}'\nssl_key_file='{key}'\n"
        )
    logfile = (root / "postgres.log").open("w")
    process = subprocess.Popen(
        [str(binaries / "postgres"), "-D", str(data)],
        env=env,
        stdout=logfile,
        stderr=subprocess.STDOUT,
    )
    admin = None
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError(
                    "PostgreSQL fixture server stopped: " + str(root / "postgres.log")
                )
            try:
                admin = psycopg.connect(
                    host="localhost",
                    port=port,
                    dbname="postgres",
                    user=os.environ.get("USER", "s-oktay"),
                    sslmode="verify-full",
                    sslrootcert=str(cert),
                    autocommit=True,
                )
                break
            except psycopg.OperationalError:
                time.sleep(0.05)
        if admin is None:
            raise RuntimeError("PostgreSQL fixture timeout")
        admin.execute(
            "CREATE TABLE records(id bigint PRIMARY KEY, name text, amount numeric(20,6))"
        )
        admin.execute("INSERT INTO records VALUES (1,'Çağrı',1.234567),(2,'Işıl',NULL)")
        admin.execute("CREATE ROLE vu_reader LOGIN")
        admin.execute("GRANT CONNECT ON DATABASE postgres TO vu_reader")
        admin.execute("GRANT USAGE ON SCHEMA public TO vu_reader")
        admin.execute("GRANT SELECT ON records TO vu_reader")
        yield dict(
            endpoint="localhost",
            port=port,
            database="postgres",
            user="vu_reader",
            ca_file=str(cert),
            admin=admin,
            root=root,
        )
    finally:
        if admin:
            admin.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        logfile.close()


@contextmanager
def mariadb_server(root, binaries, mysql=False):
    import pymysql

    root, binaries = Path(root), Path(binaries)
    cert, key = tls_files(root)
    data = root / "mariadata"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(binaries.parent / "lib")
    base = binaries.parent
    init_command = (
        [
            str(binaries / "mysqld"),
            "--no-defaults",
            "--initialize-insecure",
            "--basedir=" + str(base),
            "--datadir=" + str(data),
        ]
        if mysql
        else [
            str(binaries / "mariadb-install-db"),
            "--no-defaults",
            "--basedir=" + str(base),
            "--datadir=" + str(data),
            "--auth-root-authentication-method=normal",
            "--skip-test-db",
        ]
    )
    subprocess.run(
        init_command,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    logfile = (root / "mariadb.log").open("w")
    process = subprocess.Popen(
        [
            str(binaries / ("mysqld" if mysql else "mariadbd")),
            "--no-defaults",
            "--basedir=" + str(base),
            "--datadir=" + str(data),
            "--bind-address=127.0.0.1",
            "--port=" + str(port),
            "--socket=" + str(root / "mariadb.sock"),
            "--pid-file=" + str(root / "mariadb.pid"),
            "--ssl-cert=" + str(cert),
            "--ssl-key=" + str(key),
            "--ssl-ca=" + str(cert),
            "--skip-log-bin",
        ],
        env=env,
        stdout=logfile,
        stderr=subprocess.STDOUT,
    )
    admin = None
    try:
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError(
                    "MariaDB fixture stopped: " + str(root / "mariadb.log")
                )
            try:
                admin = pymysql.connect(
                    host="localhost",
                    port=port,
                    user="root",
                    ssl_ca=str(cert),
                    ssl_verify_cert=True,
                    ssl_verify_identity=True,
                    autocommit=True,
                )
                break
            except pymysql.MySQLError:
                time.sleep(0.05)
        if admin is None:
            raise RuntimeError("MariaDB fixture timeout")
        with admin.cursor() as cursor:
            cursor.execute("CREATE DATABASE fixture")
            cursor.execute(
                "CREATE TABLE fixture.records(id BIGINT PRIMARY KEY, amount DECIMAL(20,6)) ENGINE=InnoDB"
            )
            cursor.execute("INSERT INTO fixture.records VALUES (1,1.234567),(2,NULL)")
            cursor.execute("CREATE USER 'vu_reader'@'%' REQUIRE SSL")
            cursor.execute("GRANT SELECT ON fixture.* TO 'vu_reader'@'%'")
        yield dict(
            endpoint="localhost",
            port=port,
            user="vu_reader",
            database="fixture",
            schema="fixture",
            ca_file=str(cert),
            admin=admin,
            root=root,
        )
    finally:
        if admin:
            admin.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        logfile.close()


@contextmanager
def secret_service(root, binary):
    root = Path(root)
    env = os.environ.copy()
    for name in ("CONFIG", "STATE", "DATA", "CACHE", "RUNTIME"):
        place = root / name.lower()
        place.mkdir(mode=0o700)
        env["XDG_" + name + ("_DIR" if name == "RUNTIME" else "_HOME")] = str(place)
    env["LD_LIBRARY_PATH"] = str(Path(binary).parent.parent / "lib")
    bus = subprocess.Popen(
        ["dbus-daemon", "--session", "--nofork", "--print-address=1"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    daemon = None
    try:
        env["DBUS_SESSION_BUS_ADDRESS"] = bus.stdout.readline().strip()
        daemon = subprocess.Popen(
            [str(binary), "--foreground", "--unlock", "--components=secrets"],
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        daemon.stdin.write("fixture-keyring-unlock\n")
        daemon.stdin.close()
        import secretstorage

        for _ in range(100):
            try:
                previous = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = env["DBUS_SESSION_BUS_ADDRESS"]
                with secretstorage.dbus_init() as connection:
                    collection = secretstorage.get_default_collection(connection)
                    if not collection.is_locked():
                        break
            except Exception:
                time.sleep(0.05)
            finally:
                if previous is None:
                    os.environ.pop("DBUS_SESSION_BUS_ADDRESS", None)
                else:
                    os.environ["DBUS_SESSION_BUS_ADDRESS"] = previous
        else:
            raise RuntimeError("Secret Service fixture did not unlock")
        yield env
    finally:
        if daemon:
            daemon.terminate()
            daemon.wait(timeout=5)
        bus.terminate()
        bus.wait(timeout=5)


@contextmanager
def s3_server(root, binary):
    import boto3
    from botocore.config import Config

    root = Path(root)
    cert, key = tls_files(root)
    ports = []
    for _ in range(12):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            ports.append(sock.getsockname()[1])
    config = root / "s3.json"
    config.write_text(
        json.dumps(
            dict(
                identities=[
                    dict(
                        name="fixture-admin",
                        credentials=[
                            dict(
                                accessKey="fixture-admin", secretKey="fixture-admin-key"
                            )
                        ],
                        actions=["Admin", "Read", "Write", "List", "Tagging"],
                    ),
                    dict(
                        name="fixture-reader",
                        credentials=[
                            dict(
                                accessKey="fixture-reader",
                                secretKey="fixture-reader-key",
                            )
                        ],
                        actions=["Read", "List"],
                    ),
                ]
            )
        )
    )
    logfile = (root / "seaweedfs.log").open("w")
    command = [
        str(binary),
        "mini",
        "-dir=" + str(root / "data"),
        "-ip=127.0.0.1",
        "-ip.bind=127.0.0.1",
        "-s3.config=" + str(config),
        "-s3.cert.file=" + str(cert),
        "-s3.key.file=" + str(key),
        "-s3.port.iceberg=0",
        "-s3.port.lance=0",
    ]
    options = (
        "master.port",
        "master.port.grpc",
        "volume.port",
        "volume.port.grpc",
        "filer.port",
        "filer.port.grpc",
        "s3.port",
        "s3.port.grpc",
        "s3.port.https",
        "admin.port",
        "admin.port.grpc",
        "debug.port",
    )
    command += [
        "-" + name + "=" + str(port) for name, port in zip(options, ports, strict=True)
    ]
    (root / "data").mkdir()
    process = subprocess.Popen(command, stdout=logfile, stderr=subprocess.STDOUT)
    endpoint = "https://localhost:" + str(ports[8])
    admin = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id="fixture-admin",
        aws_secret_access_key="fixture-admin-key",
        region_name="us-east-1",
        verify=str(cert),
        config=Config(
            signature_version="s3v4",
            connect_timeout=1,
            read_timeout=1,
            retries={"total_max_attempts": 1},
            s3={"addressing_style": "path"},
            proxies={},
        ),
    )
    try:
        for _ in range(200):
            if process.poll() is not None:
                raise RuntimeError(
                    "SeaweedFS fixture stopped: " + str(root / "seaweedfs.log")
                )
            try:
                admin.list_buckets()
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("S3 fixture timeout")
        admin.create_bucket(Bucket="fixture-data")
        yield dict(
            endpoint=endpoint,
            ca_file=str(cert),
            admin=admin,
            root=root,
            secret=json.dumps(
                dict(access_key="fixture-reader", secret_key="fixture-reader-key")
            ),
        )
    finally:
        admin.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        logfile.close()
