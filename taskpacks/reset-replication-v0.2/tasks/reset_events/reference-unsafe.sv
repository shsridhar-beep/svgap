module reset_events(input logic clk, input logic ext_rst_n, input logic event_valid,
                    output logic [7:0] event_count);

always_ff @(posedge clk or negedge ext_rst_n) begin
  if (!ext_rst_n) event_count <= 8'h00;
    else if (event_valid) event_count <= event_count + 1'b1;
end
endmodule
