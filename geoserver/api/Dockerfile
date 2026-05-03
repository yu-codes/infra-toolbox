FROM python:3.12-slim

WORKDIR /app

# 安裝 Python 依賴（先複製 requirements.txt 以利用 Docker layer 快取）
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式源碼
# geoserverClient.py 位於 geoserver/ 根目錄（與 GeoServer 容器共用同一個客戶端模組）
COPY geoserverClient.py .
COPY api/config.py .
COPY api/main.py .

# -----------------------------------------------------------------------
# 使用者權限設定
# -----------------------------------------------------------------------
# GeoServer 容器預設以 geoserver 使用者（UID 1000, GID 1000）運行
# API 容器同樣建立 UID 1000 使用者，確保寫入 /shared 的檔案兩端皆可讀取
# 這是解決共享目錄使用者權限問題的關鍵
RUN groupadd -g 1000 geoapi \
    && useradd -u 1000 -g geoapi -s /bin/bash -m geoapi \
    && chown -R geoapi:geoapi /app

USER geoapi

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
