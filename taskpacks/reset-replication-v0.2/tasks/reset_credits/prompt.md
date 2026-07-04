Generate a synthesizable module matching:

```systemverilog
module reset_credits(input logic clk, input logic async_reset_n,
                     input logic consume, input logic replenish,
                     output logic [3:0] credits);
```

Increment credits on `replenish`, decrement on `consume` when nonzero, and hold
when both are asserted. Reset the count to zero. `async_reset_n` is deliberately
asynchronous at assertion; design a synchronous release path before ordinary
state exits reset. The implementation will be checked for reset-domain safety.

Return plain SystemVerilog only.
