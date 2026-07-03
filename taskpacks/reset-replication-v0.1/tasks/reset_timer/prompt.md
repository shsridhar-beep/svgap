Produce a production-oriented SystemVerilog implementation of:

```systemverilog
module reset_timer(input logic clk, input logic por_n, input logic load,
                   input logic [3:0] load_value, output logic expired);
```

Loading captures `load_value`; the timer counts down once per clock and asserts
`expired` at zero. `por_n` comes from an asynchronous power-on source. Assertion
is asynchronous, but the reset seen by functional sequential state must be
released synchronously to `clk`. The design must be portable synthesizable RTL.

Output the module only.
