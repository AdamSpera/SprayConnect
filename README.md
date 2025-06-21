# Conex

A CLI tool to connect to network devices with automatic fallback across SSH, Telnet, and console methods.

## Installation

```bash
pip install .
```

The command `conex` will be available on your `PATH`.

## Usage

```bash
conex <hostname> [--config path/to/hosts.yaml]
```

By default the configuration is loaded from `~/.conex/hosts.yaml` or from the
path specified in the `CONEX_HOSTS_FILE` environment variable.

### Configuration file format

The host configuration can be written either using legacy keys or a more flexible
list of connection entries. The simplest approach is to provide a list directly
under each hostname. Each item declares the connection `type` and credentials:

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

You may also nest the list under a `connections:` key if you prefer to keep
additional settings alongside the host entry.

The legacy dictionary style with `ssh`, `telnet`, and `console` keys is still
accepted for backward compatibility. Connection attempts always occur in the
following order when present: `ssh`, `telnet`, `console_ssh`, then
`console_telnet`.

Every entry must include a `port` field. This keeps the format consistent and
avoids relying on implicit defaults.
