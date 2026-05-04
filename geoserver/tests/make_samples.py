#!/usr/bin/env python3
"""
產生明顯可於地圖上識別的 GeoServer 測試資料。

輸出（tests/samples/ 目錄）：
  taiwan_grid.zip    - 台灣四象限格網多邊形圖層（SHP, WGS84）
  taiwan_grid.sld    - 對應的四色 SLD 樣式
  taiwan_rainbow.tif - 彩虹漸層 3-band RGB GeoTIFF（台灣範圍, 512×512, WGS84）

執行方式：
  pip install pyshp rasterio numpy
  python tests/make_samples.py

注意：
  - rasterio 在 Windows 上需迴避 PROJ 版本衝突，故使用 WKT 定義 CRS
  - 產出的 taiwan_rainbow.tif 為 3-band RGB，不需額外 SLD 即可在 GeoServer 呈現彩色
"""

import io
import sys
import zipfile
from pathlib import Path

# ── 輸出目錄 ────────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 台灣主要範圍 ────────────────────────────────────────────────────────────
TW_W, TW_E = 119.9, 122.1
TW_S, TW_N = 21.8, 25.4
TW_MID_LON = (TW_W + TW_E) / 2  # ~121.0
TW_MID_LAT = (TW_S + TW_N) / 2  # ~23.6

# WGS84 PRJ 字串（不依賴 PROJ 資料庫）
WGS84_WKT = (
    'GEOGCS["WGS 84",'
    'DATUM["WGS_1984",'
    'SPHEROID["WGS 84",6378137,298.257223563,'
    'AUTHORITY["EPSG","7030"]],'
    'AUTHORITY["EPSG","6326"]],'
    'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
    'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
    'AUTHORITY["EPSG","4326"]]'
)

# ============================================================================
# 1. Shapefile ZIP — 四象限格網多邊形
# ============================================================================


def make_taiwan_grid_zip() -> Path:
    """
    產生台灣四象限格網多邊形 Shapefile ZIP。

    格網切分：
      NW（西北）: 藍色  lon=TW_W~MID, lat=MID~TW_N
      NE（東北）: 紅色  lon=MID~TW_E, lat=MID~TW_N
      SW（西南）: 綠色  lon=TW_W~MID, lat=TW_S~MID
      SE（東南）: 橙色  lon=MID~TW_E, lat=TW_S~MID

    每個 polygon 都足夠大（約 1°×1.8°），在任何縮放級別都清晰可見。
    """
    try:
        import shapefile  # pyshp
    except ImportError:
        print("❌ 請先安裝 pyshp: pip install pyshp")
        sys.exit(1)

    shp_buf = io.BytesIO()
    shx_buf = io.BytesIO()
    dbf_buf = io.BytesIO()

    w = shapefile.Writer(
        shp=shp_buf,
        shx=shx_buf,
        dbf=dbf_buf,
        shapeType=shapefile.POLYGON,
    )
    w.field("region", "C", 2)  # NW / NE / SW / SE
    w.field("label", "C", 30)  # 中文標籤
    w.field("color", "C", 7)  # hex 色碼
    w.field("value", "N", 5, 0)  # 數值（方便測試分類樣式）

    cells = [
        (
            "NW",
            "北西（藍）",
            "#3498db",
            10,
            [
                [TW_W, TW_MID_LAT],
                [TW_MID_LON, TW_MID_LAT],
                [TW_MID_LON, TW_N],
                [TW_W, TW_N],
                [TW_W, TW_MID_LAT],
            ],
        ),
        (
            "NE",
            "北東（紅）",
            "#e74c3c",
            20,
            [
                [TW_MID_LON, TW_MID_LAT],
                [TW_E, TW_MID_LAT],
                [TW_E, TW_N],
                [TW_MID_LON, TW_N],
                [TW_MID_LON, TW_MID_LAT],
            ],
        ),
        (
            "SW",
            "西南（綠）",
            "#2ecc71",
            30,
            [
                [TW_W, TW_S],
                [TW_MID_LON, TW_S],
                [TW_MID_LON, TW_MID_LAT],
                [TW_W, TW_MID_LAT],
                [TW_W, TW_S],
            ],
        ),
        (
            "SE",
            "東南（橙）",
            "#f39c12",
            40,
            [
                [TW_MID_LON, TW_S],
                [TW_E, TW_S],
                [TW_E, TW_MID_LAT],
                [TW_MID_LON, TW_MID_LAT],
                [TW_MID_LON, TW_S],
            ],
        ),
    ]

    for region, label, color, value, ring in cells:
        w.poly([ring])
        w.record(region=region, label=label, color=color, value=value)

    w.close()

    # 打包成 ZIP，統一命名為 taiwan_grid.*
    layer_name = "taiwan_grid"
    zip_path = OUT_DIR / f"{layer_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{layer_name}.shp", shp_buf.getvalue())
        zf.writestr(f"{layer_name}.shx", shx_buf.getvalue())
        zf.writestr(f"{layer_name}.dbf", dbf_buf.getvalue())
        zf.writestr(f"{layer_name}.prj", WGS84_WKT)

    print(f"✓ {zip_path.relative_to(OUT_DIR.parent.parent)}")
    return zip_path


# ============================================================================
# 2. SLD — 四象限四色樣式
# ============================================================================


def make_taiwan_grid_sld() -> Path:
    """
    產生與 taiwan_grid.zip 對應的 SLD 1.0 樣式。
    使用 PropertyIsEqualTo 過濾 region 欄位，分別套用不同顏色。
    """
    SLD_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>taiwan_grid</Name>
    <UserStyle>
      <Name>taiwan_grid</Name>
      <FeatureTypeStyle>
        <Rule>
          <Name>NW - 北西（藍）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>NW</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#3498db</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Name>NE - 北東（紅）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>NE</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#e74c3c</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Name>SW - 西南（綠）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>SW</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#2ecc71</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Name>SE - 東南（橙）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>SE</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#f39c12</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
"""
    sld_path = OUT_DIR / "taiwan_grid.sld"
    sld_path.write_text(SLD_TEMPLATE, encoding="utf-8")
    print(f"✓ {sld_path.relative_to(OUT_DIR.parent.parent)}")
    return sld_path


# ============================================================================
# 3. GeoTIFF — 彩虹漸層 RGB
# ============================================================================


def make_taiwan_rainbow_tif() -> Path:
    """
    產生彩虹漸層 3-band RGB GeoTIFF。

    規格：
      - 範圍：台灣主要陸域（TW_W~TW_E, TW_S~TW_N）
      - 大小：512 × 512 像素
      - 色彩：彩虹色相（Hue 0°→300°）從西到東漸變，亮度從南到北漸增
      - CRS：WGS84（EPSG:4326），以 WKT 嵌入，避免 PROJ 版本衝突

    3-band RGB 無需額外 SLD，GeoServer 直接以原色渲染。
    """
    try:
        import numpy as np
        import rasterio
        from rasterio.crs import CRS
        from rasterio.transform import from_bounds
    except ImportError:
        print("❌ 請先安裝: pip install numpy rasterio")
        sys.exit(1)

    H, W = 512, 512

    # X: 西→東 (0→1)，Y: 北→南 (0→1，row 0 = 北端)
    xx = np.linspace(0.0, 1.0, W, dtype=np.float32)
    yy = np.linspace(0.0, 1.0, H, dtype=np.float32)
    X, Y = np.meshgrid(xx, yy)

    # 色相：西側（左）為紅（0°）→ 東側（右）為紫（300°）
    hue = X * 300.0  # 0..300 degrees
    sat = np.ones_like(X)
    # 亮度：北（row 0, Y=0）最亮，南（row -1, Y=1）次亮，避免全黑
    val = 0.55 + 0.45 * (1.0 - Y)  # 0.55 ~ 1.0

    # HSV → RGB（向量化，不依賴 colorsys）
    H6 = hue / 60.0  # sector 0..5
    I = H6.astype(np.int32) % 6
    F = H6 - np.floor(H6)
    P = val * (1.0 - sat)
    Q = val * (1.0 - F * sat)
    T = val * (1.0 - (1.0 - F) * sat)

    R = np.select(
        [I == 0, I == 1, I == 2, I == 3, I == 4, I == 5],
        [val, Q, P, P, T, val],
    )
    G = np.select(
        [I == 0, I == 1, I == 2, I == 3, I == 4, I == 5],
        [T, val, val, Q, P, P],
    )
    B = np.select(
        [I == 0, I == 1, I == 2, I == 3, I == 4, I == 5],
        [P, P, T, val, val, Q],
    )

    data = np.stack(
        [
            (R * 255).astype(np.uint8),
            (G * 255).astype(np.uint8),
            (B * 255).astype(np.uint8),
        ],
        axis=0,
    )  # shape: (3, H, W)

    transform = from_bounds(TW_W, TW_S, TW_E, TW_N, W, H)

    tif_path = OUT_DIR / "taiwan_rainbow.tif"
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=H,
        width=W,
        count=3,
        dtype=np.uint8,
        crs=CRS.from_wkt(WGS84_WKT),
        transform=transform,
        compress="lzw",  # 無損壓縮，縮小檔案
        photometric="RGB",  # 明確標記 RGB，GeoServer 可正確辨識
    ) as ds:
        ds.write(data)

    size_kb = tif_path.stat().st_size // 1024
    print(
        f"✓ {tif_path.relative_to(OUT_DIR.parent.parent)}  ({size_kb} KB, 3-band RGB, {W}×{H}px)"
    )
    return tif_path


# ============================================================================
# 4. 上傳腳本（可選）：直接透過 API 上傳
# ============================================================================


def upload_samples_via_api(
    base_url: str = "http://localhost:8000", workspace: str = "demo"
) -> None:
    """
    （可選）直接透過 FastAPI 上傳產生的樣本資料。
    需要容器正在運行且 workspace 已存在。
    """
    try:
        import requests
    except ImportError:
        print("❌ 請先安裝: pip install requests")
        return

    grid_zip = OUT_DIR / "taiwan_grid.zip"
    rainbow_tif = OUT_DIR / "taiwan_rainbow.tif"

    if not grid_zip.exists() or not rainbow_tif.exists():
        print("❌ 請先執行此腳本產生樣本資料")
        return

    # 建立工作區（若不存在）
    r = requests.post(f"{base_url}/workspaces", data={"workspace": workspace})
    print(f"[WS] {r.json().get('message', r.text)}")

    # 上傳 SHP ZIP
    layer_name_shp = "taiwan_grid"
    store_name_shp = f"{layer_name_shp}_store"
    with open(grid_zip, "rb") as f:
        r = requests.post(
            f"{base_url}/workspaces/{workspace}/stores/{store_name_shp}/layers/shp-zip",
            data={"layer_name": layer_name_shp},
            files={"file": ("taiwan_grid.zip", f, "application/zip")},
        )
    body = r.json()
    if r.ok:
        print(f"[SHP] 上傳成功 → {body.get('service_urls', {}).get('wms', '')}")
    else:
        print(f"[SHP] 上傳失敗: {body.get('detail', r.text)}")

    # 上傳 GeoTIFF
    layer_name_tif = "taiwan_rainbow"
    store_name_tif = f"{layer_name_tif}_store"
    with open(rainbow_tif, "rb") as f:
        r = requests.post(
            f"{base_url}/workspaces/{workspace}/stores/{store_name_tif}/layers/tiff",
            data={"layer_name": layer_name_tif},
            files={"file": ("taiwan_rainbow.tif", f, "image/tiff")},
        )
    body = r.json()
    if r.ok:
        print(f"[TIFF] 上傳成功 → {body.get('service_urls', {}).get('wms', '')}")
    else:
        print(f"[TIFF] 上傳失敗: {body.get('detail', r.text)}")

    # 上傳 SLD 並套用到 taiwan_grid
    sld_path = OUT_DIR / "taiwan_grid.sld"
    if sld_path.exists():
        with open(sld_path, "rb") as f:
            r = requests.post(
                f"{base_url}/styles",
                data={"style_name": "taiwan_grid"},
                files={"file": ("taiwan_grid.sld", f, "application/xml")},
            )
        if r.ok:
            # 套用樣式（三層路徑）
            requests.put(
                f"{base_url}/workspaces/{workspace}/stores/{store_name_shp}/layers/{layer_name_shp}/style",
                data={"style_name": "taiwan_grid"},
            )
            print("[SLD] 樣式上傳並套用成功")
        else:
            print(f"[SLD] 樣式上傳失敗: {r.json().get('detail', r.text)}")

    print(f"\n🌍 前端地圖: http://localhost:8000")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="產生 GeoServer 測試用樣本資料")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="產生後直接透過 API 上傳至 GeoServer（需要容器運行中）",
    )
    parser.add_argument(
        "--workspace", default="demo", help="上傳目標工作區（預設: demo）"
    )
    parser.add_argument(
        "--api",
        default="http://localhost:8000",
        help="API 服務 URL（預設: http://localhost:8000）",
    )
    args = parser.parse_args()

    print("═" * 55)
    print(" 產生 GeoServer 測試樣本資料")
    print("═" * 55)

    make_taiwan_grid_zip()
    make_taiwan_grid_sld()
    make_taiwan_rainbow_tif()

    print()
    print(f"📂 輸出目錄：{OUT_DIR}")
    print()
    print("上傳方式：")
    print("  A) 前端地圖拖放上傳：http://localhost:8000")
    print("  B) 指令自動上傳：python make_samples.py --upload")
    print()

    if args.upload:
        print("═" * 55)
        print(" 自動上傳至 GeoServer")
        print("═" * 55)
        upload_samples_via_api(args.api, args.workspace)
