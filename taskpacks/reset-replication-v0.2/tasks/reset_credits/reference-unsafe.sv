module reset_credits(input logic clk, input logic async_reset_n,
                     input logic consume, input logic replenish,
                     output logic [3:0] credits);

always_ff @(posedge clk or negedge async_reset_n) begin
  if (!async_reset_n) credits <= 4'h0;
    else if (replenish && !consume) credits <= credits + 1'b1;
    else if (consume && !replenish && credits != 0) credits <= credits - 1'b1;
end
endmodule
