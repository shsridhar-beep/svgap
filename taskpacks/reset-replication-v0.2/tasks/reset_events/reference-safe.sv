module reset_events(input logic clk, input logic ext_rst_n, input logic event_valid,
                    output logic [7:0] event_count);

logic reset_meta_n, reset_sync_n;
wire local_reset_n = ext_rst_n & reset_sync_n;

always_ff @(posedge clk or negedge ext_rst_n) begin
  if (!ext_rst_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) event_count <= 8'h00;
    else if (event_valid) event_count <= event_count + 1'b1;
end
endmodule
