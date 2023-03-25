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

[Print processor schema is available here](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/blob/main/schema/print.processor.schema.json)

* `type` (mandatory)
    * For the print processor, `type` must always be `print`
* `topics` is a dictionary translating from an OBIS code to a text which
    will be printed out to the console (`stdout` or equivalent), followed by " = ",
    followed by the value. [More information on the slightly modified OBIS format used](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/tree/main/docs/obis.md)

Example:
```json
"printMode": {
    "type": "print",
    "topics": {
        "1-0:1.8.1": "Consumed Index - Daytime Tariff",
        "1-0:1.8.2": "Consumed Index - Nighttime Tariff"              
    }
},
```

#### `logger` processor

[Logger processor schema is available here](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/blob/main/schema/logger.processor.schema.json)

* `type` (mandatory)
    * For the print processor, `type` must always be `logger`
* `logLevel` (optional)
    * The log level in which the messages are logged. `INFO` by default. List of all possible levels
    is available [in the python logging library documentation](https://docs.python.org/3/library/logging.html#logging-levels)
* `topics` is a dictionary translating from an OBIS code to a text which
    will be printed out to the console (`stdout` or equivalent), followed by " = ",
    followed by the value. [More information on the slightly modified OBIS format used](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/tree/main/docs/obis.md)

Example:
```json
"printMode": {
    "type": "logger",
    "logLevel": "DEBUG",
    "topics": {
        "1-0:1.8.1": "Consumed Index/Daytime Tariff",
        "1-0:1.8.2": "Consumed Index/Nighttime Tariff"              
    }
},
```

#### `mqtt` processor

[MQTT Processor schema is available here](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/blob/main/schema/mqtt.processor.schema.json)
Common settings to all scenarios:

* `type` (mandatory)
    * For the print processor, `type` must always be `mqtt`
* `topics` (mandatory)
    * Is a map of OBIS codes to MQTT topics
* `broker` (mandatory)
    * The IP address or DNS name of the MQTT broker (e.g. MosQuiTTo server)
* `port` (optional)
    * The port number for the connection
    * By default, this is 1883 in case TLS is not used. This is 8883 if TLS is used.
    * Note it does not take into account whether the transport is `websockets` or `tcp`
* `protocol` (optional)
    * Must be one of `MQTTv31`, `MQTTv311` or `MQTTv5`
    * Note that in any case, clean_session will be set to `true`
    * Default value is the Paho MQTT default value.
* `clientId` (optional)
    * Overrides the client_id property in MQTT
    * Default value is `belgian-smartmeter-p1-to-mqtt`

##### using `websockets` connections (optional)

By default, the MQTT processor uses `tcp` connection.
If you want to use websockets you must define a `websockets` block and set the following options:

* `enabled` (mandatory) must be set to `true` to use websockets. Defaults to false.
* `path` (mandatory) must be set to the websockets endpoint name (eg `/mqtt)`.
* `headers` (optional) is a dictionary of headers to be passed to the websockets broker.

##### using `username` and `password` authentication (optional)

* `username` (optional, *mandatory if `password` is populated*)
    * The MQTT username, if any
* `password` (optional)
    * The MQTT password, if any

##### using `tls` connection (optional) and authentication (optional)


### `scheduling` Section

**Mandatory section**. TODO.