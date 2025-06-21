# Spray Connect (sc)

Spray Connect is a lightweight CLI that tries several connection methods (SSH,
Telnet and console) until one succeeds.

## Quick start

Clone the repository and run the script directly with Python:

```bash
git clone https://github.com/adamspera/spray-connect.git
cd spray-connect
python3 sc.py <hostname> --config path/to/hosts.yaml
```

## Usage

Run the CLI with a hostname:

```bash
python3 sc.py <hostname> --config path/to/hosts.yaml
```

The configuration is loaded from `~/.sc/hosts.yaml` by default or from the path
set in the `SC_HOSTS_FILE` environment variable.

### Configuration file format

Each host entry provides a list of connection methods. An example YAML file is
shown below:

```yaml
hostname1:
  - type: ssh
    ip: 192.168.1.10
    port: 22
    username: admin
    password: cisco123
  - type: telnet
    ip: 192.168.1.10
    port: 23
    username: admin
    password: cisco123
  - type: console_ssh
    ip: 192.168.1.20
    port: 2222
    username: console
    password: c0ns0le
  - type: console_telnet
    ip: 192.168.1.20
    port: 2323
    username: console
    password: c0ns0le
```

The list items share the same schema:

```
- type: <ssh|telnet|console_ssh|console_telnet>
  ip: <ip address>
  port: <integer>
  username: <optional username>
  password: <optional password>
```

You may also nest the list under a `connections:` key if you prefer to keep
additional settings alongside the host entry.

The legacy dictionary style with `ssh`, `telnet`, and `console` keys is still
accepted for backward compatibility. Connection attempts always occur in the
following order when present: `ssh`, `telnet`, `console_ssh`, then
`console_telnet`.

Every entry must include a `port` field. This keeps the format consistent and
avoids relying on implicit defaults.
