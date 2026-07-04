module reset_counter(input logic clk, input logic arst_n, input logic enable,
                     output logic [7:0] count);

always_ff @(posedge clk or negedge arst_n) begin
  if (!arst_n) count <= 8'h00;
    else if (enable) count <= count + 1'b1;
end
endmodule
