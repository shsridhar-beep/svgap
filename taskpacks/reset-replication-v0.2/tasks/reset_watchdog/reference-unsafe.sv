module reset_watchdog(input logic clk, input logic system_rst_n, input logic kick,
                      output logic timeout);
logic [2:0] quiet_cycles;
always_ff @(posedge clk or negedge system_rst_n) begin
  if (!system_rst_n) begin
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
