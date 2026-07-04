module reset_fsm(input logic clk, input logic reset_n, input logic start,
                 output logic busy, output logic done);
logic [1:0] phase;
logic reset_meta_n, reset_sync_n;
wire local_reset_n = reset_n & reset_sync_n;

always_ff @(posedge clk or negedge reset_n) begin
  if (!reset_n) begin
    reset_meta_n <= 1'b0;
    reset_sync_n <= 1'b0;
  end else begin
    reset_meta_n <= 1'b1;
    reset_sync_n <= reset_meta_n;
  end
end

always_ff @(posedge clk or negedge local_reset_n) begin
  if (!local_reset_n) begin
      phase <= 2'd0; busy <= 1'b0; done <= 1'b0;
    end else begin
      done <= 1'b0;
      case (phase)
        2'd0: if (start) begin phase <= 2'd1; busy <= 1'b1; end
        2'd1: phase <= 2'd2;
        2'd2: begin phase <= 2'd0; busy <= 1'b0; done <= 1'b1; end
        default: begin phase <= 2'd0; busy <= 1'b0; done <= 1'b0; end
      endcase
    end
end
endmodule
