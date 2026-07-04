module reset_status(input logic clk, input logic rst_n, input logic set_fault,
                    input logic clear_fault, output logic fault_latched);

always_ff @(posedge clk or negedge rst_n) begin
  if (!rst_n) fault_latched <= 1'b0;
    else if (clear_fault) fault_latched <= 1'b0;
    else if (set_fault) fault_latched <= 1'b1;
end
endmodule
