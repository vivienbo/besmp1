# Configuration Files and Features

## SmartMeter Reader config.json

[JSON Schema is available here](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/blob/main/schema/config.schema.json)

### `core` Section

**Optional section** with two properties:
* `restartOnFailure` (optional)
    * Must be set to `true` if you want the configuration to be reloaded
    and all threads to be restarted in case an `Exception` is met in
    any of the daemon threads of the application.
    * Default value is `false`
* `smartMeterTimeZone` (optional)
    * Must be set to your SmartMeter Time Zone (eg in Belgium, all SmartMeters)
    currently use the `Europe/Brussels`.
    * List of [all possible values is available here](https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568)
    * Default value is to use your operating system local timezone (using `tzlocal.get_localzone()`)

### `healthControl` Section

**Optional section** with two properties:
* `enable` (mandatory)
    * If `healthControl` section exists, it is mandatory to set the `enable` property
    to either `true` or `false`
    * Setting this to `true` will create a `HealthControlThread` which will stop
    automatically all threads after a duration of `lifetimeCycles * timeout`.
    * Interaction with `restartOnFailure`:
        * if set to `false`, the program ends after `HealthControlThread` stopped all daemon threads.
        * If set to `true`, the program restarts all threads after `HealthControlThread` stopped
        all daemon threads. Including a new HealthControlThread.
    * Default value if `healthControl` does not exists: `false`
* `lifetimeCycles` (optional)
    * The number of cycles for which `HealthControlThread` will run until it terminates
    all daemon threads. Each cycle has a duration of `timeout` seconds.
    * Default value is `2160`

### TODO