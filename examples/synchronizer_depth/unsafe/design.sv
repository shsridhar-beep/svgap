module synchronizer_depth (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic data_in,
    output logic data_out
);
    logic src_value;
    logic meta;

    always_ff @(posedge src_clk) begin
        if (!rst_n) src_value <= 1'b0;
        else src_value <= data_in;
    end

    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            meta     <= 1'b0;
            data_out <= 1'b0;
        end else begin
            meta     <= src_value;
            data_out <= meta;
        end
    end
endmodule
