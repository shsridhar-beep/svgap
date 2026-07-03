Write a production-quality SystemVerilog module with exactly this interface:

```systemverilog
module mode_crossing(input logic cfg_clk, input logic core_clk, input logic rst_n,
                     input logic set_mode, input logic mode_in,
                     output logic core_mode);
```

`cfg_clk` and `core_clk` are unrelated asynchronous clocks. On a `cfg_clk` edge with
`set_mode` high, store `mode_in` as a persistent configuration bit. Transfer that
stable bit reliably to `core_mode`. Active-low `rst_n` clears all state.

Return only the complete SystemVerilog module, with no prose or markdown fences.
