module gray_counter (
    input  logic src_clk,
    input  logic dst_clk,
    input  logic rst_n,
    input  logic enable,
    output logic [3:0] dst_count
);
    logic [3:0] src_count;
    logic [3:0] gray_src;
    logic [3:0] gray_meta;
    logic [3:0] gray_sync;

    always_ff @(posedge src_clk) begin
        if (!rst_n) begin
            src_count <= 0;
            gray_src  <= 0;
        end else if (enable) begin
            src_count <= src_count + 1'b1;
            gray_src  <= (src_count + 1'b1) ^ ((src_count + 1'b1) >> 1);
        end
    end

    // Controlled reference shape: registered Gray code and two destination stages.
    always_ff @(posedge dst_clk) begin
        if (!rst_n) begin
            gray_meta <= 0;
            gray_sync <= 0;
        end else begin
            gray_meta <= gray_src;
            gray_sync <= gray_meta;
        end
    end

    always_comb begin
        dst_count[3] = gray_sync[3];
        dst_count[2] = dst_count[3] ^ gray_sync[2];
        dst_count[1] = dst_count[2] ^ gray_sync[1];
        dst_count[0] = dst_count[1] ^ gray_sync[0];
    end
endmodule
