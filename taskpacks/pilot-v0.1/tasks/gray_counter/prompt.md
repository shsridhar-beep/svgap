Write a production-quality SystemVerilog module with exactly this interface:

```systemverilog
module gray_counter(input logic src_clk, input logic dst_clk, input logic rst_n,
                    input logic enable, output logic [3:0] dst_count);
```

`src_clk` and `dst_clk` are unrelated asynchronous clocks. Increment a 4-bit source
counter on each `src_clk` edge while `enable` is high. Make its value available as
`dst_count` in the destination domain using a Gray-coded transfer so independently
sampled bus bits cannot create an incoherent binary value. Active-low `rst_n` clears
all state.

Return only the complete SystemVerilog module, with no prose or markdown fences.
