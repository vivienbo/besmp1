# OBIS Format information

## Slightly modified OBIS Format Support

The standard OBIS Format is composed of a sequence in the form of `n-n:nnn.nnn.nnn(.nnn)(\*nnn)`. Examples are listed below.
The OBIS Format used in this project configuration files is slightly modified to introduce a `/nnn` in case of multiple values.

Take this line as example:
`1-0:1.6.0(230318200000W)(04.470*kW)`

Its meaning is:
* First value: the date at which the 15-min average peak consumption of the month happened
* Second value: the peak consumption in kW at the peak time

If you want to refer to the date, you would need to use `1-0:1.6.0/0` syntax.
And if you want to refer to the peak consumption, you would need to use `1-0:1.6.0/1`.

This is useful for electricity network operators who implemented a capacitive pricing model (eg Fluvius in Flanders).

## Example output from Ores SmartMeter (Siconia S211)

Replacements for privacy:
* n = [0-9], numeric digit
* h = [0-9A-F], hexadecimal digit

```
/FLU5\nnnnnnnnn_A

0-0:96.1.4(50217)
0-0:96.1.1(nnnnnnnnnnnnnnnnnnnnnnnnnnnn)
0-0:1.0.0(230319201739W)
1-0:1.8.1(000316.698*kWh)
1-0:1.8.2(000407.323*kWh)
1-0:2.8.1(000001.447*kWh)
1-0:2.8.2(000000.000*kWh)
0-0:96.14.0(0002)
1-0:1.4.0(00.377*kW)
1-0:1.6.0(230318200000W)(04.470*kW)
0-0:98.1.0(0)(1-0:1.6.0)(1-0:1.6.0)()
1-0:1.7.0(02.959*kW)
1-0:2.7.0(00.000*kW)
1-0:21.7.0(02.959*kW)
1-0:22.7.0(00.000*kW)
1-0:32.7.0(232.2*V)
1-0:31.7.0(013.06*A)
0-0:96.3.10(1)
0-0:17.0.0(999.9*kW)
1-0:31.4.0(999*A)
0-0:96.13.0()
!hhhh
```

## Reference document

[More information on OBIS meaning (IEC62056)](https://www.promotic.eu/en/pmdoc/Subsystems/Comm/PmDrivers/IEC62056_OBIS.htm)

## Belgian-specific information (not in reference document)

| OBIS Code | Meaning |
| -- | -- |
| 1.0.0 | The date of this measurement in YYYYMMDDhhmmss**X** format <br/>where **X** is  **W** for Winter and **S** for Summer |
| 1.4.0 | *TODO* |
| 1.6.0 | *TODO* |
| 1.8.1 | Energy consumed in Daytime tariff |
| 1.8.2 | Energy consumed in Nighttime tariff |
| 2.8.1 | Energy injected in Daytime tariff |
| 2.8.2 | Energy injected in Nighttime tariff |
| 17.0.0 | *TODO* |
| **P**1.4.0 | Used if the Smart Meter is asked to limit maximum current in Phase **P** (eg budget meter mode) |
| 96.1.1 | *TODO* |
| 96.3.10 | *TODO* |
| 96.13.0 | Text Message from the electricity network operator |
| 96.14.0 | *TODO* |
| 98.1.0 | *TODO* |

Where P means:
| P value | Phase number |
| -- | -- |
| 3 | Phase 1 (used by single and three-phase meters) |
| 5 | Phase 2 (only for three-phase meters) |
| 7 | Phase 3 (only for three-phase meters) |
