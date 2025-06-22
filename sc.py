#!/usr/bin/env python3
import argparse
import os
import socket
import subprocess
import sys
import shutil
import telnetlib

# Basic ANSI color codes
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

DASH = "\u2013"

# Options to permit legacy SSH algorithms and keys
SSH_LEGACY_OPTS = [
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'UserKnownHostsFile=/dev/null',
    '-o', 'HostKeyAlgorithms=+ssh-rsa,ssh-dss',
    '-o', 'KexAlgorithms=+diffie-hellman-group1-sha1,diffie-hellman-group14-sha1,diffie-hellman-group-exchange-sha1',
    '-o', 'PubkeyAcceptedKeyTypes=+ssh-rsa,ssh-dss'
]


def color(text, col):
    return f"{col}{text}{RESET}"


def parse_hosts_yaml(path):
    """Very small YAML parser for the limited hosts schema."""
    hosts = {}
    with open(path) as fh:
        lines = fh.readlines()
    current_host = None
    current_entry = None
    for raw in lines:
        line = raw.rstrip()  # keep indentation
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line.startswith(' '):
            # top-level key
            if line.endswith(':'):
                current_host = line[:-1].strip()
                hosts[current_host] = []
            continue
        # inside host
        if line.lstrip().startswith('- '):
            current_entry = {}
            hosts[current_host].append(current_entry)
            line = line.lstrip()[2:]
            if line:
                if ':' in line:
                    k, v = line.split(':', 1)
                    current_entry[k.strip()] = v.strip()
            continue
        if current_entry is not None:
            line = line.strip()
            if ':' in line:
                k, v = line.split(':', 1)
                current_entry[k.strip()] = v.strip()
    return hosts


def check_port(ip, port, timeout=3):
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((ip, port))
        sock.close()
        return True
    except Exception:
        return False


def check_ssh_compat(ip, port, username):
    cmd = ['ssh', '-o', 'BatchMode=yes'] + SSH_LEGACY_OPTS + [
        '-p', str(port), f'{username}@{ip}', 'exit']
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=10)
    except Exception:
        return False
    err = result.stderr.decode()
    incompatible = [
        'Host key verification failed',
        'no matching key exchange',
        'Unable to negotiate',
        'no matching host key type'
    ]
    if any(msg in err for msg in incompatible):
        return False
    return True


def launch_ssh(ip, port, username, password=None):
    # Build base ssh command with legacy options
    base_cmd = ['ssh'] + SSH_LEGACY_OPTS + ['-p', str(port), f'{username}@{ip}']
    if password and shutil.which('sshpass'):
        cmd = ['sshpass', '-p', password] + base_cmd
    else:
        if password:
            print(color('! sshpass not available, password will be requested.', YELLOW))
        cmd = base_cmd
    os.execvp(cmd[0], cmd)


def try_telnet(ip, port, username=None, password=None):
    try:
        tn = telnetlib.Telnet(ip, port, timeout=5)
    except Exception:
        return False
    # look for login or username prompt
    idx, _, _ = tn.expect([b'login:', b'Login:', b'Username:', b'username:'], timeout=3)
    if idx == -1:
        tn.close()
        return False
    if username:
        tn.write(username.encode('ascii') + b'\n')
        if password:
            tn.expect([b'Password:'], timeout=3)
            tn.write(password.encode('ascii') + b'\n')
    tn.interact()
    return True


def main():
    parser = argparse.ArgumentParser(description='SprayConnect CLI')
    parser.add_argument('hostname', help='hostname to connect to')
    parser.add_argument('--config', default='hosts.yaml', help='hosts YAML file')
    args = parser.parse_args()

    try:
        hosts = parse_hosts_yaml(args.config)
    except FileNotFoundError:
        print(color(f"Config file '{args.config}' not found", RED))
        sys.exit(1)

    if args.hostname not in hosts:
        print(color(f"Hostname '{args.hostname}' not found in {args.config}", RED))
        sys.exit(1)

    print(f"Connecting to '{args.hostname}' using config file '{args.config}'")
    for entry in hosts[args.hostname]:
        typ = entry.get('type', '').lower()
        ip = entry.get('ip')
        port = int(entry.get('port', 0))
        user = entry.get('username')
        pwd = entry.get('password')
        label = typ.upper()
        print(f"\nTrying {label} on {ip}:{port}...")
        if check_port(ip, port):
            print(color('✓ Port reachable', GREEN))
        else:
            print(color('✗ Port unreachable', RED))
            print(f"{DASH} Skipping {label} session")
            continue

        if typ == 'ssh':
            if check_ssh_compat(ip, port, user):
                print(color('✓ Compatible keys', GREEN))
                print(color('✓ Launching SSH session', GREEN))
                launch_ssh(ip, port, user, pwd)
                return
            else:
                print(color('✗ Incompatible keys', RED))
                print(f"{DASH} Skipping SSH session")
        elif typ == 'telnet':
            success = try_telnet(ip, port, user, pwd)
            if success:
                return
            else:
                print(color('✗ Intractable', RED))
                print(f"{DASH} Skipping TELNET session")
        else:
            print(color(f"Unknown connection type '{typ}'", RED))


if __name__ == '__main__':
    main()
