Write a production-quality SystemVerilog module with exactly this interface:

```systemverilog
module level_crossing(input logic src_clk, input logic dst_clk, input logic rst_n,
                      input logic toggle, output logic dst_level);
```

`src_clk` and `dst_clk` are unrelated asynchronous clocks. In the source domain,
each asserted `toggle` toggles a persistent level. Transfer that level reliably to
`dst_level` in the destination domain. Active-low `rst_n` clears all state.

Return only the complete SystemVerilog module, with no prose or markdown fences.
