Implement this exact SystemVerilog interface:

```systemverilog
module reset_status(input logic clk, input logic rst_n, input logic set_fault,
                    input logic clear_fault, output logic fault_latched);
```

Latch a fault when `set_fault` is high and clear it when `clear_fault` is high,
with clear taking priority. The incoming active-low chip reset must assert without
waiting for a clock, yet its deassertion must not expose any storage element to an
asynchronous reset release. Use generic synthesizable constructs only.

Respond with code only.
