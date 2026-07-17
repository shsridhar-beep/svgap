FROM python:3.12.10-slim-bookworm

ARG TARGETARCH
ARG OSS_CAD_DATE=20260508
ARG OSS_CAD_SHA256_AMD64=c71735b02df363e2ad8e9f129e477e4f31b18d6532e9bed92eb8ad296101cb6f
ARG OSS_CAD_SHA256_ARM64=4b056c3e999c4289db22decb9e2be06178e9c66d6f56e48d8f1c9c85d1452f72

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && case "$TARGETARCH" in \
         amd64) arch=x64; digest="$OSS_CAD_SHA256_AMD64" ;; \
         arm64) arch=arm64; digest="$OSS_CAD_SHA256_ARM64" ;; \
         *) echo "unsupported TARGETARCH: $TARGETARCH" >&2; exit 2 ;; \
       esac \
    && url="https://github.com/YosysHQ/oss-cad-suite-build/releases/download/2026-05-08/oss-cad-suite-linux-${arch}-${OSS_CAD_DATE}.tgz" \
    && curl -L --fail --output /tmp/oss-cad-suite.tgz "$url" \
    && echo "$digest  /tmp/oss-cad-suite.tgz" | sha256sum --check - \
    && mkdir -p /opt/oss-cad-suite \
    && tar -xzf /tmp/oss-cad-suite.tgz -C /opt/oss-cad-suite --strip-components=1 \
    && rm /tmp/oss-cad-suite.tgz

ENV PATH="/opt/oss-cad-suite/bin:${PATH}"
WORKDIR /opt/svgap
COPY . .
RUN python -m pip install --no-cache-dir ".[naja]" \
    && svgap doctor

WORKDIR /work
ENTRYPOINT ["svgap"]
CMD ["--help"]
