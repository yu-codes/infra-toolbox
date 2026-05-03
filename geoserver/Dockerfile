FROM docker.osgeo.org/geoserver:2.27.0

# 安裝必要套件並設定中文語系（合併為單一 RUN 指令，減少映像層數）
# 先清除可能的 stale apt lists，避免 Hash Sum mismatch 問題
RUN chmod 1777 /tmp \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        locales \
        curl \
    && sed -ie 's/# zh_TW.UTF-8 UTF-8/zh_TW.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=zh_TW.UTF-8

# 建立共享目錄
# GeoServer 以 geoserver 使用者（UID 1000）運行
# chmod 1777：設定 sticky bit，確保所有使用者可讀寫但不能刪除他人檔案
# 此步驟在映像建置時設定；Docker named volume 首次掛載時會繼承此目錄的權限
RUN mkdir -p /shared \
    && chown 1000:1000 /shared \
    && chmod 1777 /shared

EXPOSE 8080
