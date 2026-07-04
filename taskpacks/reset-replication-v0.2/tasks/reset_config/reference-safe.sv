module reset_config(input logic clk, input logic global_reset_n,
                    input logic write_en, input logic [3:0] config_in,
                    output logic [3:0] config_out);

logic reset_meta_n, reset_sync_n;
wire local_reset_n = global_reset_n & reset_sync_n;

always_ff @(posedge clk or negedge global_reset_n) begin
  if (!global_reset_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) config_out <= 4'h0;
    else if (write_en) config_out <= config_in;
end
endmodule
