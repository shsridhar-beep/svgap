module reset_counter(input logic clk, input logic arst_n, input logic enable,
                     output logic [7:0] count);

logic reset_meta_n, reset_sync_n;
wire local_reset_n = arst_n & reset_sync_n;

always_ff @(posedge clk or negedge arst_n) begin
  if (!arst_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) count <= 8'h00;
    else if (enable) count <= count + 1'b1;
end
endmodule
