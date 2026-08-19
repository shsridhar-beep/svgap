module async_fifo_shape (
    input logic wr_clk, rd_clk, rst_n,
    output logic [2:0] wr_pointer_seen,
    output logic [2:0] rd_pointer_seen
);
    logic [2:0] wr_gray, rd_gray;
    logic [2:0] wr_gray_meta, wr_gray_sync;
    logic [2:0] rd_gray_meta, rd_gray_sync;

    always_ff @(posedge wr_clk) begin
        if (!rst_n) wr_gray <= 0;
        else wr_gray <= wr_gray + 1'b1;
    end
    always_ff @(posedge rd_clk) begin
        if (!rst_n) rd_gray <= 0;
        else rd_gray <= rd_gray + 1'b1;
    end
    always_ff @(posedge rd_clk) begin
        if (!rst_n) begin wr_gray_meta <= 0; wr_gray_sync <= 0; end
        else begin wr_gray_meta <= wr_gray; wr_gray_sync <= wr_gray_meta; end
    end
    always_ff @(posedge wr_clk) begin
        if (!rst_n) begin rd_gray_meta <= 0; rd_gray_sync <= 0; end
        else begin rd_gray_meta <= rd_gray; rd_gray_sync <= rd_gray_meta; end
    end
    assign wr_pointer_seen = wr_gray_sync;
    assign rd_pointer_seen = rd_gray_sync;
endmodule
