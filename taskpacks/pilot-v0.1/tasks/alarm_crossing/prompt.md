Write a production-quality SystemVerilog module with exactly this interface:

```systemverilog
module alarm_crossing(input logic sensor_clk, input logic mgmt_clk, input logic rst_n,
                      input logic temp_high, input logic voltage_low,
                      output logic mgmt_alarm);
```

`sensor_clk` and `mgmt_clk` are unrelated asynchronous clocks. Form the alarm as
`temp_high && voltage_low` in the sensor domain and transfer it reliably to
`mgmt_alarm` without allowing combinational glitches into the clock-domain crossing.
Active-low `rst_n` clears all state.

Return only the complete SystemVerilog module, with no prose or markdown fences.
