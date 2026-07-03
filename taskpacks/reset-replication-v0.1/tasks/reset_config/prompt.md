Write a complete portable SystemVerilog module:

```systemverilog
module reset_config(input logic clk, input logic global_reset_n,
                    input logic write_en, input logic [3:0] config_in,
                    output logic [3:0] config_out);
```

Capture `config_in` when `write_en` is asserted. The global active-low reset is
allowed to assert asynchronously. Its release into the clock domain must be
synchronized, and the configuration register must not deassert directly from
the raw reset pin. Initialize configuration to zero.

Do not include prose or markdown.
