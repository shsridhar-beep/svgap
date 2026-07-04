Implement the following RTL interface in SystemVerilog:

```systemverilog
module reset_watchdog(input logic clk, input logic system_rst_n, input logic kick,
                      output logic timeout);
```

Pulse `timeout` after four consecutive clock cycles without `kick`; a kick
restarts the interval. `system_rst_n` is an asynchronous active-low system reset.
Assertion must be asynchronous, but all operational state must resume only from
a reset release synchronized to `clk`. Use standard synthesizable RTL and return
code only.
