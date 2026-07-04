module reset_status(input logic clk, input logic rst_n, input logic set_fault,
                    input logic clear_fault, output logic fault_latched);

logic reset_meta_n, reset_sync_n;
wire local_reset_n = rst_n & reset_sync_n;

always_ff @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) fault_latched <= 1'b0;
    else if (clear_fault) fault_latched <= 1'b0;
    else if (set_fault) fault_latched <= 1'b1;
end
endmodule
