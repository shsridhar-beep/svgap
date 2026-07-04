Supply only synthesizable SystemVerilog for:

```systemverilog
module reset_events(input logic clk, input logic ext_rst_n, input logic event_valid,
                    output logic [7:0] event_count);
```

Count cycles on which `event_valid` is high. Clear the count on reset. The
external reset can arrive asynchronously and must clear promptly, but release
from reset must be clock-aligned throughout the design so no counter bit sees a
raw asynchronous deassertion. Avoid library-specific attributes or cells.
