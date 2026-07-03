Write only a complete synthesizable SystemVerilog module:

```systemverilog
module reset_fsm(input logic clk, input logic reset_n, input logic start,
                 output logic busy, output logic done);
```

On `start`, assert `busy` for two clock cycles, then pulse `done` for one cycle.
The external active-low `reset_n` may assert between clock edges. Reset assertion
must take effect asynchronously, while removal must be synchronized so recovery
and removal timing is protected for every state-holding element. Do not instantiate
technology-specific cells.
