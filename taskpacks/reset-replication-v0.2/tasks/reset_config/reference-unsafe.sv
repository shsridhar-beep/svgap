module reset_config(input logic clk, input logic global_reset_n,
                    input logic write_en, input logic [3:0] config_in,
                    output logic [3:0] config_out);

always_ff @(posedge clk or negedge global_reset_n) begin
  if (!global_reset_n) config_out <= 4'h0;
    else if (write_en) config_out <= config_in;
end
endmodule
