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
* if `timeout` isn't set, default value is `5` (seconds)

### `p1Transform` section

**Optional section** which contains an unlimited number of transformation objects.
Transformations allows to do basic calculation on OBIS values to create a new OBIS value.
Objects are composed of:

* `object name` (mandatory)
    * Must be in the OBIS Format (eg `1-0:1.8.0`).
    * If the object name corresponds to an existing object, it replaces this object from
    the SmartMeter output.
    * If the object uses result from another transformation, it must be a transformation
    declared later in the file (avoids infinite loops)
* `operation` (mandatory)
    * `sum` is currently the only supported operation
* `operands` list (mandatory)
    * list of the OBIS codes (`string`) which are to be summed. Not that the transformation
    does **not** check that the units are consistent when doing the `operation`.
* `unit` (optional)
    * Default value is `kWh`
    * Defines the unit of the result

Typical use case is for the total consumed kWh index (`1-0:1.8.0`) and total injected kWh index (`1-0:2.8.0`) displayed on the SmartMeter screen but which is no transmitted through the Serial Port.

Example for a `p1Transform` block containing only the `1-0:1.8.0` definition:
```json
"p1Transform": {
    "1-0:1.8.0": {
        "operation": "sum",
        "operands": [
            "1-0:1.8.1",
            "1-0:1.8.2"
        ],
        "unit": "kWh"
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
If you want to use websockets you must define a `websockets` **block** and set the following options:

* `enabled` (mandatory) must be set to `true` to use websockets. Defaults to false.
* `path` (mandatory) must be set to the websockets endpoint name (eg `/mqtt)`.
* `headers` (optional) is a dictionary of headers to be passed to the websockets broker.

Example of `websockets` block:
```json
"websockets": {
    "enabled": true,
    "path": "/mqtt_ws",
    "headers": {
        "X-CUSTOM-HEADER", "abcdefghihjKLMNOPQRST1111"
    }
}
```

##### using `username` and `password` authentication (optional)

These items are to be put direcly in the MQTT processor definition:

* `username` (optional, *mandatory if `password` is populated*)
    * The MQTT username, if any
* `password` (optional)
    * The MQTT password, if any

##### using `tls` connection (optional) and authentication (optional)

Use of TLS requires the creation of a `tls` **block** which can have the following properties:

* TLS connectivity properties:
    * `useTLS` (mandatory if `tls` block exists)
        * should be set to `true` to use TLS or `false` not to use it
        * if there is no `tls` block, is set to `false`
    * `setTLSInsecure` (optional)
        * Default value is `false`
    * `rootCAFileName` (optional)
        * Default value is `config.crt`
        * Path is relative to the `/config` folder
        * Providing a certificate is mandatory. Example is given for *Let's Encrypt*
    * `tlsVersion` (optional)
        * Default value `PROTOCOL_TLSv1_2`
        * Possible values are `PROTOCOL_TLSv1_2`, `PROTOCOL_TLSv1_1`, `PROTOCOL_TLSv1`, `PROTOCOL_SSLv3`, `PROTOCOL_SSLv23`, `PROTOCOL_SSLv2`
    * `ciphers` (optional)
        * Default value are python `ssl` library default ciphers
    * `certReqs` (optional)
        * Default value is `CERT_NONE`
        * Possible values are `CERT_NONE`, `CERT_OPTIONAL`, `CERT_REQUIRED`

* TLS authentication properties:
    * `certfile` (optional, *mandatory for TLS authentication*)
        * Path is relative to the `/config` folder
        * Must contrain the public certificate of the client
    * `keyfile` (optional, *mandatory for TLS authentication*)
        * Path is relative to the `/config` folder
        * Must contrain the private key of the client

### `scheduling` Section

Scheduling section is made of a table of schedule objects with the following fields:

* `cronFormat` (mandatory)
    * The time and periodicity at which the processor will be called
    * Uses [UNIX cron format](https://crontab.guru/) with an optional 6th field for seconds
    * Exemple: 1 2 * * * 0/30: at 2h01m00s and  2h01m30s everyday
* `processor` (mandatory)
    * Must be the name of a [processor](#processors-section) that will be triggered
* `mode` (mandatory)
    * Two modes are supported:
        * `average`: each second, the value will be added to a list and at the time of the trigger,
        the mathematical mean will be calculated and transmitted
        * `current`: the instant / current value is transmitted when the schedule is triggered
* `applyTo` (mandatory)
    * a list of [OBIS codes](https://github.com/vivienbo/belgian-smartmeter-p1-to-mqtt/blob/main/docs/obis.md)
    in a slightly modified format for multi-values
    * only the listed OBIS codes will be transmitted, and only if they were received

Example of a script which runs every 30 seconds and sends the 30s average (mathematical mean)
of the instant injected power, consumed power, intensity and tension.

```json
{
    "cronFormat": "* * * * * 0/30",
    "processor": "mqttShirka",
    "mode": "average",
    "applyTo": [
        "1-0:21.7.0",
        "1-0:22.7.0",
        "1-0:31.7.0",
        "1-0:32.7.0"
    ]
}
```