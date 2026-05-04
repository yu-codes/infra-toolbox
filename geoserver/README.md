# GeoServer 地圖管理系統 — 使用說明

## 快速開始

### 1. 啟動服務
```bash
cd geoserver/
docker compose up -d
```

服務會在以下位置就緒（約 30 秒）：
- **前端地圖管理**: http://localhost:8000
- **GeoServer Web UI**: http://localhost:8080/geoserver
- **API 文件**: http://localhost:8000/docs (FastAPI 自動生成)

### 2. 生成測試資料
```bash
cd tests/
python make_samples.py --upload --workspace demo
```

這會產生並自動上傳：
- `taiwan_grid.zip` — 台灣四象限 SHP 圖層（藍/紅/綠/橙 四色）
- `taiwan_rainbow.tif` — 彩虹漸層 RGB GeoTIFF（512×512 像素）
- `taiwan_grid.sld` — 對應的四色樣式

### 3. 在前端地圖上傳圖層

#### A. 使用前端拖放界面
1. 開啟 http://localhost:8000
2. 確保左側工作區為 `demo`（或自行建立）
3. **上傳 Shapefile ZIP**：
   - 輸入圖層名稱（如 `my_vector`）
   - 拖放或點擊選擇 `.zip` 檔案（需含 `.shp`、`.shx`、`.dbf`、`.prj`）
   - 點擊「上傳圖層」按鈕
   - 地圖中央會立即出現新圖層（藍色高亮）

4. **上傳 GeoTIFF**：
   - 輸入圖層名稱（如 `my_raster`）
   - 拖放或點擊選擇 `.tif` 或 `.tiff` 檔案
   - 點擊「上傳圖層」按鈕
   - 地圖中央會立即出現新圖層

#### B. 自動上傳測試資料
```bash
python tests/make_samples.py --upload --workspace demo
```

### 4. 地圖互動

| 操作 | 說明 |
|---|---|
| **眼睛圖標** | 切換圖層顯示/隱藏 |
| **外連圖標** | 在新分頁預覽圖層的 WMS 渲染結果 |
| **刪除圖標** | 刪除圖層（同步刪除 GeoServer 中的資源） |
| **刷新圖標** | 從 GeoServer 重新整理圖層列表 |

### 5. 進階操作

#### 建立新工作區
1. 在左側「工作區」欄位輸入名稱
2. 點擊「建立」按鈕
3. 新工作區會出現在下方 chip 中

#### 上傳自訂 SLD 樣式
通過 API 或 GeoServer Web UI（http://localhost:8080/geoserver） 上傳：
```bash
curl -X POST http://localhost:8000/styles \
  -F "style_name=my_style" \
  -F "file=@my_style.sld"
```

然後在 GeoServer Web UI 中將樣式套用到圖層。

---

## 目錄結構

```
geoserver/
├── docker-compose.yaml       # 容器編排設定
├── Dockerfile                # GeoServer 基礎映像配置
├── geoserverClient.py        # GeoServer REST API 客戶端
│
├── api/                       # FastAPI 應用
│   ├── main.py               # API 路由與前端入口
│   ├── config.py             # 環境設定
│   ├── requirements.txt       # Python 依賴
│   ├── Dockerfile            # API 容器映像
│   └── static/
│       └── index.html        # 前端地圖管理界面
│
└── tests/
    ├── test_geoserver_api.py # 32 項整合測試
    ├── make_samples.py       # 測試資料產生指令
    └── samples/              # 輸出目錄
        ├── taiwan_grid.zip
        ├── taiwan_grid.sld
        └── taiwan_rainbow.tif
```

---

## 常見問題

### Q: 上傳後地圖上沒有看到圖層
**A:** 
1. 檢查瀏覽器主控台（F12）是否有 JavaScript 錯誤
2. 確認左側「已載入圖層」清單中有新圖層
3. 點擊眼睛圖標確保圖層可見（應顯示綠色眼睛）
4. 檢查 GeoServer 日誌：`docker logs geoserver | tail -30`

### Q: Shapefile ZIP 上傳時出現「缺少必要文件」
**A:**
ZIP 必須包含以下四個檔案（檔名前綴相同）：
- `.shp` — 幾何資料
- `.shx` — 索引
- `.dbf` — 屬性資料
- `.prj` — 座標參照系統定義

### Q: GeoTIFF 不顯示或顯示為黑色
**A:**
確保 GeoTIFF：
- 包含有效的座標參照系統資訊（CRS/EPSG）
- 像素值在合理範圍內（0-255 或浮點）
- 支援的頻段數：1 (灰階)、3 (RGB)、4 (RGBA)

### Q: 如何重新開始（清除所有圖層）
**A:**
```bash
docker compose down -v          # 刪除容器與命名卷
docker compose up -d            # 重新啟動（乾淨狀態）
```

---

## API 端點概述

### 前端
- `GET /` — 地圖管理界面
- `GET /layers` — 列出所有圖層（JSON）
- `GET /health` — API 健康狀態

### 工作區管理
- `POST /workspaces` — 建立工作區
- `GET /workspaces` — 列出工作區
- `DELETE /workspaces/{workspace}` — 刪除工作區

### 圖層管理  
- `POST /layers/shp-zip` — 上傳 Shapefile ZIP
- `POST /layers/tiff` — 上傳 GeoTIFF
- `DELETE /layers/{workspace}/{layer_name}` — 刪除圖層
- `GET /layers/{workspace}/{layer_name}/wfs-url` — WFS 查詢 URL

### 樣式管理
- `POST /styles` — 上傳 SLD 樣式
- `PUT /layers/{workspace}/{layer_name}/style` — 套用樣式到圖層

詳細文件：http://localhost:8000/docs

---

## 技術棧

| 元件 | 版本/說明 |
|---|---|
| GeoServer | 2.27.0 (OSGeo 官方映像) |
| FastAPI | 0.115.5 |
| Leaflet | 1.9.4 (OpenStreetMap) |
| Python | 3.12 (API 容器) |
| 測試框架 | pytest (32 項端對端測試) |

---

## 開發與測試

### 執行整合測試
```bash
cd tests/
pip install -r requirements.txt
pytest test_geoserver_api.py -v
```

預期結果：**32 passed** ✓

### 檢視服務日誌
```bash
docker compose logs -f geoserver    # GeoServer
docker compose logs -f api          # API & 前端
```

### 存取 GeoServer 管理介面
- URL: http://localhost:8080/geoserver
- 帳號：`admin`
- 密碼：`geoserver`

---

## 最佳實踐清單

- ✅ 使用 named volume 確保資料持久化
- ✅ 容器使用相同 UID (1000) 確保共享目錄權限
- ✅ 直接 ZIP 上傳而非 file:// URI（規避 sandbox 限制）
- ✅ Health check 確保服務依賴順序
- ✅ 32 項自動化測試涵蓋 CRUD 與 WMS 渲染驗證
- ✅ 前端地圖實時反映後端變化

---

最後更新：2026-05-04
