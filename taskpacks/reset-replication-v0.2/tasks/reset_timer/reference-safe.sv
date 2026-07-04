module reset_timer(input logic clk, input logic por_n, input logic load,
                   input logic [3:0] load_value, output logic expired);
logic [3:0] remaining;
logic reset_meta_n, reset_sync_n;
wire local_reset_n = por_n & reset_sync_n;

always_ff @(posedge clk or negedge por_n) begin
  if (!por_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) begin
      remaining <= 4'h0; expired <= 1'b0;
    end else if (load) begin
      remaining <= load_value; expired <= (load_value == 0);
    end else if (remaining > 1) begin
      remaining <= remaining - 1'b1; expired <= 1'b0;
    end else if (remaining == 1) begin
      remaining <= 0; expired <= 1'b1;
    end
end
endmodule
