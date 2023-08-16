# Installing the arweave-api as a service

The arweave-api can be run as a systemd service.

The service will be installed at
`/etc/systemd/system/arkly-arweave-api.service`. The service will be called:
`arkly-arweave-api`.

After an update, i.e. you've fetched and merged, or 'pull'-ed your changes from
the remote branch, run, from this folder: `./install-service.sh`. You will be
prompted to run the script as sudo.

The `install-service.sh` script will:

1. Copy the service definition `arkly-arweave-api.service` to `/etc/systemd`.
2. Reload the service daemon.
3. Restart the service.
4. Enable/ensure the service restarts at startup.
5. Display the service status, e.g. to see if there are any errors.

## Interacting with your service

* Restart: `service arkly-arweave-api restart`.
* Status: `service arkly-arweave-api status`.

## Monitoring

To monitor the service (follow along with output from the service), the output
can be found in `journalctl`.

* `journalctl -f -u arkly-arweave-api`

To access historical logs, omit the `-f` and run:

* `journalctl -u arkly-arweave-api`

## Debugging

The `journalctl` output is the first place to look. It should show the root
cause, e.g. as the service installation script doesn't install new pypi
requirements, and the service won't start properly, module import errors should
show up in `journalctl`. To fix that particular issue, run
`python -m pip install -r requirements/requirements.txt` from the root of this
repository.

## Information about systemd

A useful tutorial for creating a Linux service can be found below from Benjamin
Morel.

* [Creating a Linux service with systemd][morel-1].

[morel-1]: https://medium.com/@benmorel/creating-a-linux-service-with-systemd-611b5c8b91d6
