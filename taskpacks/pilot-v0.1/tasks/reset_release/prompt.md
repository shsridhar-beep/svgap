Write a production-quality SystemVerilog module with exactly this interface:

```systemverilog
module reset_release(input logic clk, input logic arst_n, input logic enable,
                     output logic [3:0] count);
```

The external active-low reset must assert asynchronously but release synchronously
to `clk`. After safe reset release, increment `count` on each enabled clock edge.
Do not rely on vendor-specific primitives or annotations.

Return only the complete SystemVerilog module, with no prose or markdown fences.
