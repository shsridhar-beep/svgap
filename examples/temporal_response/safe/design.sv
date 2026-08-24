module response_engine (
    input  logic clk,
    input  logic rst_n,
    input  logic start,
    output logic done
);
    logic busy;
    logic [2:0] count;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            busy <= 1'b0;
            count <= '0;
            done <= 1'b0;
        end else begin
            done <= 1'b0;
            if (start && !busy) begin
                busy <= 1'b1;
                count <= '0;
            end else if (busy && count == 3'd2) begin
                busy <= 1'b0;
                done <= 1'b1;
            end else if (busy) begin
                count <= count + 1'b1;
            end
        end
    end
endmodule
