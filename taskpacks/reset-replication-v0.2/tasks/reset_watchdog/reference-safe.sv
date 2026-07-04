module reset_watchdog(input logic clk, input logic system_rst_n, input logic kick,
                      output logic timeout);
logic [2:0] quiet_cycles;
logic reset_meta_n, reset_sync_n;
wire local_reset_n = system_rst_n & reset_sync_n;

always_ff @(posedge clk or negedge system_rst_n) begin
  if (!system_rst_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) begin
      quiet_cycles <= 0; timeout <= 1'b0;
    end else if (kick) begin
      quiet_cycles <= 0; timeout <= 1'b0;
    end else if (quiet_cycles == 3) begin
      quiet_cycles <= quiet_cycles; timeout <= 1'b1;
    end else begin
      quiet_cycles <= quiet_cycles + 1'b1; timeout <= 1'b0;
    end
end
endmodule
