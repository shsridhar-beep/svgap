Write a production-quality SystemVerilog module with exactly this interface:

```systemverilog
module comb_crossing(input logic src_clk, input logic dst_clk, input logic rst_n,
                     input logic [1:0] src_data, output logic dst_parity);
```

`src_clk` and `dst_clk` are unrelated asynchronous clocks. Compute XOR parity of
`src_data` in the source domain and transfer the result reliably to `dst_parity`
without allowing combinational glitches into the clock-domain crossing. Active-low
`rst_n` clears all state.

Return only the complete SystemVerilog module, with no prose or markdown fences.
