module reset_credits(input logic clk, input logic async_reset_n,
                     input logic consume, input logic replenish,
                     output logic [3:0] credits);

logic reset_meta_n, reset_sync_n;
wire local_reset_n = async_reset_n & reset_sync_n;

always_ff @(posedge clk or negedge async_reset_n) begin
  if (!async_reset_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) credits <= 4'h0;
    else if (replenish && !consume) credits <= credits + 1'b1;
    else if (consume && !replenish && credits != 0) credits <= credits - 1'b1;
end
endmodule
