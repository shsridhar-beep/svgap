module reset_release (
    input  logic clk,
    input  logic arst_n,
    input  logic enable,
    output logic [3:0] count
);
    logic rst_meta;
    logic rst_sync;
    wire local_rst_n = arst_n & rst_sync;

    always_ff @(posedge clk or negedge arst_n) begin
        if (!arst_n) begin
            rst_meta <= 1'b0;
            rst_sync <= 1'b0;
        end else begin
            rst_meta <= 1'b1;
            rst_sync <= rst_meta;
        end
    end

    always_ff @(posedge clk or negedge local_rst_n) begin
        if (!local_rst_n)
            count <= 0;
        else if (enable)
            count <= count + 1'b1;
    end
endmodule
