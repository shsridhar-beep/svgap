module reset_timer(input logic clk, input logic por_n, input logic load,
                   input logic [3:0] load_value, output logic expired);
logic [3:0] remaining;
always_ff @(posedge clk or negedge por_n) begin
  if (!por_n) begin
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
