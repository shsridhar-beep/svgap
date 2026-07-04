Create a synthesizable SystemVerilog module with exactly this interface:

```systemverilog
module reset_counter(input logic clk, input logic arst_n, input logic enable,
                     output logic [7:0] count);
```

`arst_n` is an external active-low reset. It must assert asynchronously and
deassert synchronously to `clk`, including for the counter state—not merely for
an auxiliary reset flag. After safe release, increment `count` on enabled clock
edges. Use no vendor primitives.

Return only the module, without markdown or explanation.
