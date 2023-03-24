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
        all daemon threads. Including a new `HealthControlThread`.
    * Default value if `healthControl` does not exists: `false`
* `lifetimeCycles` (optional)
    * The number of cycles for which `HealthControlThread` will run until it terminates
    all daemon threads. Each cycle has a duration of `timeout` seconds.
    * Default value is `2160`

### `serialPortConfig` section

**Mandatory section** with three properties:
* `port`, `baudrate` and `timeout`: as per [PySerial native port documentation](https://pyserial.readthedocs.io/en/latest/pyserial_api.html#native-ports)
* if `timeout` isn't set, default value is `5`

### `p1Transform` section

**Optional section** which contains an unlimited number of transformation objects.
Transformations allows to do basic calculation on OBIS values to create a new OBIS value.
Objects are composed of:

* `object name` must be in the OBIS Format (eg `1-0:1.8.0`).
    * If the object name corresponds to an existing object, it replaces this object from
    the SmartMeter output.
    * If the object uses result from another transformation, it must be a transformation
    declared later in the file (avoids infinite loops)
* `operation` property
    * `sum` is currently the only supported operation
* `operands` list
    * list of the OBIS codes (`string`) which are to be summed. Not that the transformation
    does **not** check that the units are consistent when doing the `operation`.

Typical use case is for the total consumed kWh index (`1-0:1.8.0`) and total injected kWh index (`1-0:2.8.0`) displayed on the SmartMeter screen but which is no transmitted through the Serial Port.

Example for a `p1Transform` block containing only the `1-0:1.8.0` definition:
```json
"p1Transform": {
    "1-0:1.8.0": {
        "operation": "sum",
        "operands": [
            "1-0:1.8.1",
            "1-0:1.8.2"
        ]
    }
}
```

### `processors` Section

**Mandatory section**. Must contain at least one processor otherwise the application will never
take any action on read values.

#### `print` processor

* `Type` must always be `print`
* `topics` is a dictionary translating from an OBIS code to a text which
    will be printed out to the console (`stdout` or equivalent), followed by 

Example:
```json
"printMode": {
    "type": "print",
    "topics": {
        "1-0:1.8.1": "Consumed Index - Daytime Tariff",
        "1-0:1.8.2": "Consumed Index - Nighttime Tariff",
        "1-0:2.8.0": "smartmeter/electricity/reading/injection/total",
        "1-0:2.8.1": "smartmeter/electricity/reading/injection/day_tariff",
        "1-0:2.8.2": "smartmeter/electricity/reading/injection/night_tariff",
        "1-0:21.7.0": "smartmeter/electricity/instant/L1/power/consumption",
        "1-0:22.7.0": "smartmeter/electricity/instant/L1/power/injection",
        "1-0:31.7.0": "smartmeter/electricity/instant/L1/intensity",
        "1-0:32.7.0": "smartmeter/electricity/instant/L1/tension"                
    }
},
```

#### `logger` processor

#### `mqtt` processor

[Click here if you need more information on the OBIS format and example of Belgian SmartMeter output](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/tree/main/docs/obis.md)

### `scheduling` Section

**Mandatory section**. TODO.