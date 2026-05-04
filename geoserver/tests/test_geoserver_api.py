"""
GeoServer API 整合測試

測試對象：運行中的 geoserver_api 容器（http://localhost:8000）
測試範疇：Workspace / Layer（SHP ZIP / GeoTIFF）/ Style 的完整 CRUD + WMS 渲染驗證

測資自動生成：
  - Shapefile ZIP: 使用 pyshp 產生台灣座標系統（WGS84）點圖層
  - GeoTIFF:       使用 rasterio + numpy 產生 10×10 像素台灣範圍小影像
  - SLD:           使用字串模板產生最小合法 SLD

執行方式：
  cd geoserver/tests
  pip install -r requirements.txt
  pytest test_geoserver_api.py -v
"""

import io
import zipfile
import textwrap

import httpx
import numpy as np
import pytest
import rasterio
import shapefile  # pyshp
from rasterio.crs import CRS
from rasterio.transform import from_bounds

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:8000"
GEOSERVER_URL = "http://localhost:8080/geoserver"
TEST_WORKSPACE = "test_ws_integration"
TEST_LAYER_SHP = "test_point_layer"
TEST_LAYER_TIFF = "test_raster_layer"
TEST_STYLE = "test_red_point_style"
TEST_STORE_SHP = f"{TEST_LAYER_SHP}_store"
TEST_STORE_TIFF = f"{TEST_LAYER_TIFF}_store"

client = httpx.Client(base_url=BASE_URL, timeout=60.0)
geoserver_client = httpx.Client(base_url=GEOSERVER_URL, timeout=60.0)


# ===========================================================================
# 測資產生工具函數
# ===========================================================================


def make_shapefile_zip(layer_name: str) -> bytes:
    """
    產生包含 WGS84 點圖層的 Shapefile ZIP。

    使用 pyshp 在台北附近（121.5654, 25.0330）建立一個點，
    並附上 WGS84 PRJ 字串，ZIP 內所有檔案以 layer_name 命名。
    """
    shp_buf = io.BytesIO()
    shx_buf = io.BytesIO()
    dbf_buf = io.BytesIO()

    w = shapefile.Writer(
        shp=shp_buf, shx=shx_buf, dbf=dbf_buf, shapeType=shapefile.POINT
    )
    w.field("name", "C", 40)
    w.field("value", "N", 10, 2)
    # 加入台北、高雄兩個測試點
    w.point(121.5654, 25.0330)
    w.record(name="Taipei", value=1.0)
    w.point(120.3010, 22.6273)
    w.record(name="Kaohsiung", value=2.0)
    w.close()

    # WGS84 PRJ 字串（GeoServer 需要此檔來識別座標系）
    prj_content = (
        'GEOGCS["WGS 84",'
        'DATUM["WGS_1984",'
        'SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],'
        'UNIT["degree",0.0174532925199433],'
        'AUTHORITY["EPSG","4326"]]'
    )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{layer_name}.shp", shp_buf.getvalue())
        zf.writestr(f"{layer_name}.shx", shx_buf.getvalue())
        zf.writestr(f"{layer_name}.dbf", dbf_buf.getvalue())
        zf.writestr(f"{layer_name}.prj", prj_content)

    return zip_buf.getvalue()


def make_geotiff(layer_name: str) -> bytes:
    """
    產生 10×10 像素、WGS84 座標系的 GeoTIFF 測資。

    涵蓋範圍約為台灣西部（120°E-121°E, 22°N-23°N），
    使用 rasterio 確保 GeoServer 可正確辨識座標參照系統。
    使用 WKT 字串避免 PROJ 資料庫版本衝突問題。
    """
    data = np.random.randint(50, 200, (1, 10, 10), dtype=np.uint8)
    transform = from_bounds(120.0, 22.0, 121.0, 23.0, 10, 10)

    # 使用 WKT 避免 PROJ database 版本衝突（Windows 環境常見）
    wgs84_wkt = (
        'GEOGCS["WGS 84",'
        'DATUM["WGS_1984",'
        'SPHEROID["WGS 84",6378137,298.257223563,'
        'AUTHORITY["EPSG","7030"]],'
        'AUTHORITY["EPSG","6326"]],'
        'PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],'
        'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],'
        'AUTHORITY["EPSG","4326"]]'
    )

    buf = io.BytesIO()
    with rasterio.open(
        buf,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype=np.uint8,
        crs=CRS.from_wkt(wgs84_wkt),
        transform=transform,
    ) as ds:
        ds.write(data)

    return buf.getvalue()


def make_sld(style_name: str) -> str:
    """產生最小合法 SLD v1.0 樣式（紅色圓點，半徑 6px）。"""
    return textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <StyledLayerDescriptor version="1.0.0"
          xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
          xmlns="http://www.opengis.net/sld"
          xmlns:ogc="http://www.opengis.net/ogc"
          xmlns:xlink="http://www.w3.org/1999/xlink"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
          <NamedLayer>
            <Name>{style_name}</Name>
            <UserStyle>
              <Name>{style_name}</Name>
              <FeatureTypeStyle>
                <Rule>
                  <PointSymbolizer>
                    <Graphic>
                      <Mark>
                        <WellKnownName>circle</WellKnownName>
                        <Fill>
                          <CssParameter name="fill">#FF0000</CssParameter>
                        </Fill>
                      </Mark>
                      <Size>12</Size>
                    </Graphic>
                  </PointSymbolizer>
                </Rule>
              </FeatureTypeStyle>
            </UserStyle>
          </NamedLayer>
        </StyledLayerDescriptor>
    """)


# ===========================================================================
# 測試前置／清理
# ===========================================================================


@pytest.fixture(scope="module", autouse=True)
def setup_workspace():
    """在整個測試模組開始前建立工作區，結束後刪除（含所有圖層）。"""
    # 若已存在，先刪除再建立（確保乾淨環境）
    r = client.delete(f"/workspaces/{TEST_WORKSPACE}")
    # 忽略不存在的錯誤

    r = client.post("/workspaces", data={"workspace": TEST_WORKSPACE})
    assert r.status_code == 200, f"建立工作區失敗: {r.text}"

    yield  # 執行所有測試

    # 測試結束後清理
    client.delete(f"/workspaces/{TEST_WORKSPACE}")


# ===========================================================================
# 健康檢查
# ===========================================================================


class TestHealth:
    def test_api_health(self):
        """API 服務應正常運行。"""
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ===========================================================================
# Workspace 管理
# ===========================================================================


class TestWorkspace:
    def test_list_workspaces_includes_test_ws(self):
        """工作區列表應包含測試工作區。"""
        r = client.get("/workspaces")
        assert r.status_code == 200
        workspaces = r.json()["workspaces"]
        assert (
            TEST_WORKSPACE in workspaces
        ), f"工作區 {TEST_WORKSPACE} 不存在: {workspaces}"

    def test_create_duplicate_workspace_returns_error(self):
        """重複建立工作區應回傳錯誤（非 200）。"""
        r = client.post("/workspaces", data={"workspace": TEST_WORKSPACE})
        assert r.status_code != 200, "重複建立工作區不應成功"

    def test_get_workspace_layers_empty(self):
        """剛建立的工作區應無圖層。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/layers")
        assert r.status_code == 200
        assert r.json()["layers"] == []

    def test_get_workspace_stores_empty(self):
        """剛建立的工作區應無 Store。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/stores")
        assert r.status_code == 200
        assert r.json()["stores"] == []


# ===========================================================================
# Vector Layer - Shapefile ZIP
# ===========================================================================


class TestShpZipLayer:
    def test_upload_shp_zip_success(self):
        """上傳合法 Shapefile ZIP 應成功並回傳結構化資訊。"""
        zip_data = make_shapefile_zip(TEST_LAYER_SHP)
        files = {"file": (f"{TEST_LAYER_SHP}.zip", zip_data, "application/zip")}
        data = {"layer_name": TEST_LAYER_SHP}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_SHP}/layers/shp-zip",
            files=files,
            data=data,
        )
        assert r.status_code == 200, f"上傳 SHP ZIP 失敗: {r.text}"

        body = r.json()
        assert body["workspace"] == TEST_WORKSPACE
        assert body["store"] == TEST_STORE_SHP
        assert body["layer"] == TEST_LAYER_SHP
        assert body["data_type"] == "vector"
        assert "wms" in body["service_urls"]
        assert "wfs" in body["service_urls"]

    def test_layer_appears_in_workspace(self):
        """上傳後圖層應出現在工作區列表中。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/layers")
        assert r.status_code == 200
        layers = r.json()["layers"]
        assert TEST_LAYER_SHP in layers, f"圖層 {TEST_LAYER_SHP} 未出現在: {layers}"

    def test_store_appears_in_workspace(self):
        """上傳後 Store 應出現在工作區 Store 列表中。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/stores")
        assert r.status_code == 200
        store_names = [s["name"] for s in r.json()["stores"]]
        assert (
            TEST_STORE_SHP in store_names
        ), f"Store {TEST_STORE_SHP} 未出現在: {store_names}"

    def test_upload_shp_zip_overwrite(self):
        """重複上傳同名圖層應成功覆寫（update=overwrite）。"""
        zip_data = make_shapefile_zip(TEST_LAYER_SHP)
        files = {"file": (f"{TEST_LAYER_SHP}.zip", zip_data, "application/zip")}
        data = {"layer_name": TEST_LAYER_SHP}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_SHP}/layers/shp-zip",
            files=files,
            data=data,
        )
        assert r.status_code == 200, f"覆寫 SHP ZIP 失敗: {r.text}"

    def test_upload_shp_zip_invalid_format(self):
        """上傳非 ZIP 檔案應回傳 400。"""
        files = {"file": ("bad_file.txt", b"not a zip", "text/plain")}
        data = {"layer_name": "bad_layer"}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/bad_store/layers/shp-zip",
            files=files,
            data=data,
        )
        assert r.status_code == 400

    def test_upload_shp_zip_missing_prj(self):
        """ZIP 缺少 .prj 應回傳 400。"""
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zf:
            zf.writestr("layer.shp", b"fake shp")
            zf.writestr("layer.shx", b"fake shx")
            zf.writestr("layer.dbf", b"fake dbf")
            # 故意不加 .prj
        files = {"file": ("incomplete.zip", zip_buf.getvalue(), "application/zip")}
        data = {"layer_name": "incomplete_layer"}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/incomplete_store/layers/shp-zip",
            files=files,
            data=data,
        )
        assert r.status_code == 400

    def test_get_wfs_url(self):
        """應能取得 WFS URL 字串。"""
        r = client.get(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_SHP}/layers/{TEST_LAYER_SHP}/wfs-url"
        )
        assert r.status_code == 200
        wfs_url = r.json()["wfs_url"]
        assert TEST_WORKSPACE in wfs_url
        assert TEST_LAYER_SHP in wfs_url
        assert "WFS" in wfs_url

    def test_wms_getmap_renders_image(self):
        """WMS GetMap 請求應回傳有效的 PNG 圖片（驗證圖層可渲染）。"""
        params = {
            "service": "WMS",
            "version": "1.1.0",
            "request": "GetMap",
            "layers": f"{TEST_WORKSPACE}:{TEST_LAYER_SHP}",
            "bbox": "119,21,123,26",
            "width": "256",
            "height": "256",
            "srs": "EPSG:4326",
            "format": "image/png",
        }
        r = geoserver_client.get(f"/{TEST_WORKSPACE}/wms", params=params)
        assert r.status_code == 200, f"WMS GetMap 失敗: {r.status_code} {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith(
            "image/png"
        ), f"回傳非 PNG 格式: {r.headers.get('content-type')}"
        # PNG 檔案標頭: 137 80 78 71 (即 \x89PNG)
        assert r.content[:4] == b"\x89PNG", "回傳的資料不是有效 PNG"
        assert len(r.content) > 100, "PNG 檔案過小，渲染可能失敗"

    def test_wfs_getfeature_returns_geojson(self):
        """WFS GetFeature 請求應回傳有效的 GeoJSON。"""
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": f"{TEST_WORKSPACE}:{TEST_LAYER_SHP}",
            "outputFormat": "application/json",
        }
        r = geoserver_client.get("/wfs", params=params)
        assert r.status_code == 200, f"WFS GetFeature 失敗: {r.status_code}"
        data = r.json()
        assert data["type"] == "FeatureCollection"
        assert (
            len(data["features"]) == 2
        ), f"預期 2 個 feature，得到 {len(data['features'])}"


# ===========================================================================
# Raster Layer - GeoTIFF
# ===========================================================================


class TestTiffLayer:
    def test_upload_tiff_success(self):
        """上傳合法 GeoTIFF 應成功並回傳結構化資訊。"""
        tif_data = make_geotiff(TEST_LAYER_TIFF)
        files = {"file": (f"{TEST_LAYER_TIFF}.tif", tif_data, "image/tiff")}
        data = {"layer_name": TEST_LAYER_TIFF}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_TIFF}/layers/tiff",
            files=files,
            data=data,
        )
        assert r.status_code == 200, f"上傳 GeoTIFF 失敗: {r.text}"

        body = r.json()
        assert body["workspace"] == TEST_WORKSPACE
        assert body["store"] == TEST_STORE_TIFF
        assert body["layer"] == TEST_LAYER_TIFF
        assert body["data_type"] == "raster"
        assert "wms" in body["service_urls"]
        assert "wcs" in body["service_urls"]

    def test_tiff_layer_appears_in_workspace(self):
        """上傳後 GeoTIFF 圖層應出現在工作區列表中。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/layers")
        assert r.status_code == 200
        layers = r.json()["layers"]
        assert TEST_LAYER_TIFF in layers, f"圖層 {TEST_LAYER_TIFF} 未出現在: {layers}"

    def test_tiff_store_appears_in_workspace(self):
        """上傳後 CoverageStore 應出現在工作區 Store 列表中且類型為 raster。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/stores")
        assert r.status_code == 200
        stores = r.json()["stores"]
        raster_store_names = [s["name"] for s in stores if s["type"] == "raster"]
        assert (
            TEST_STORE_TIFF in raster_store_names
        ), f"CoverageStore {TEST_STORE_TIFF} 未出現在: {stores}"

    def test_upload_tiff_overwrite(self):
        """重複上傳同名 GeoTIFF 應成功覆寫。"""
        tif_data = make_geotiff(TEST_LAYER_TIFF)
        files = {"file": (f"{TEST_LAYER_TIFF}.tif", tif_data, "image/tiff")}
        data = {"layer_name": TEST_LAYER_TIFF}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_TIFF}/layers/tiff",
            files=files,
            data=data,
        )
        assert r.status_code == 200, f"覆寫 GeoTIFF 失敗: {r.text}"

    def test_upload_tiff_invalid_extension(self):
        """上傳非 TIFF 格式應回傳 400。"""
        files = {"file": ("bad.jpg", b"not a tiff", "image/jpeg")}
        data = {"layer_name": "bad_raster"}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/bad_raster_store/layers/tiff",
            files=files,
            data=data,
        )
        assert r.status_code == 400

    def test_upload_tiff_extension(self):
        """支援 .tiff 副檔名。"""
        tif_data = make_geotiff("ext_test_tiff")
        files = {"file": ("ext_test_tiff.tiff", tif_data, "image/tiff")}
        data = {"layer_name": "ext_test_tiff"}

        r = client.post(
            f"/workspaces/{TEST_WORKSPACE}/stores/ext_test_tiff_store/layers/tiff",
            files=files,
            data=data,
        )
        assert r.status_code == 200, f".tiff 副檔名上傳失敗: {r.text}"

    def test_wms_getmap_tiff_renders_image(self):
        """GeoTIFF 圖層的 WMS GetMap 請求應回傳有效的 PNG 圖片。"""
        params = {
            "service": "WMS",
            "version": "1.1.0",
            "request": "GetMap",
            "layers": f"{TEST_WORKSPACE}:{TEST_LAYER_TIFF}",
            "bbox": "120,22,121,23",
            "width": "256",
            "height": "256",
            "srs": "EPSG:4326",
            "format": "image/png",
        }
        r = geoserver_client.get(f"/{TEST_WORKSPACE}/wms", params=params)
        assert (
            r.status_code == 200
        ), f"WMS GetMap (TIFF) 失敗: {r.status_code} {r.text[:200]}"
        assert r.headers.get("content-type", "").startswith(
            "image/png"
        ), f"回傳非 PNG 格式: {r.headers.get('content-type')}"
        assert r.content[:4] == b"\x89PNG", "回傳的資料不是有效 PNG"
        assert len(r.content) > 100, "PNG 檔案過小，渲染可能失敗"

    def test_wcs_describe_coverage(self):
        """WCS DescribeCoverage 請求應成功回傳 XML。"""
        params = {
            "service": "WCS",
            "version": "2.0.1",
            "request": "DescribeCoverage",
            "coverageId": f"{TEST_WORKSPACE}__{TEST_LAYER_TIFF}",
        }
        r = geoserver_client.get(f"/{TEST_WORKSPACE}/wcs", params=params)
        assert r.status_code == 200, f"WCS DescribeCoverage 失敗: {r.status_code}"
        assert (
            "CoverageDescription" in r.text or "coverageDescription" in r.text.lower()
        )


# ===========================================================================
# Style 管理
# ===========================================================================


class TestStyle:
    def test_upload_style_success(self):
        """上傳合法 SLD 樣式應成功。"""
        sld_content = make_sld(TEST_STYLE)
        files = {
            "file": (
                f"{TEST_STYLE}.sld",
                sld_content.encode("utf-8"),
                "application/xml",
            )
        }
        data = {"style_name": TEST_STYLE}

        r = client.post("/styles", files=files, data=data)
        assert r.status_code == 200, f"上傳 SLD 失敗: {r.text}"

    def test_style_appears_in_list(self):
        """上傳後樣式應出現在全域樣式列表中。"""
        r = client.get("/styles")
        assert r.status_code == 200
        styles = r.json()["styles"]
        assert TEST_STYLE in styles, f"樣式 {TEST_STYLE} 未出現在: {styles}"

    def test_publish_style_to_layer(self):
        """將樣式套用到圖層應成功。"""
        r = client.put(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_SHP}/layers/{TEST_LAYER_SHP}/style",
            data={"style_name": TEST_STYLE},
        )
        assert r.status_code == 200, f"套用樣式失敗: {r.text}"

    def test_wms_getmap_with_style_renders(self):
        """套用樣式後，WMS GetMap 請求應正常渲染。"""
        params = {
            "service": "WMS",
            "version": "1.1.0",
            "request": "GetMap",
            "layers": f"{TEST_WORKSPACE}:{TEST_LAYER_SHP}",
            "styles": TEST_STYLE,
            "bbox": "119,21,123,26",
            "width": "256",
            "height": "256",
            "srs": "EPSG:4326",
            "format": "image/png",
        }
        r = geoserver_client.get(f"/{TEST_WORKSPACE}/wms", params=params)
        assert r.status_code == 200, f"WMS GetMap with style 失敗: {r.status_code}"
        assert r.content[:4] == b"\x89PNG", "套用樣式後渲染失敗"

    def test_upload_style_invalid_extension(self):
        """上傳非 .sld 格式應回傳 400。"""
        files = {"file": ("bad.xml", b"<xml/>", "application/xml")}
        data = {"style_name": "bad_style"}

        r = client.post("/styles", files=files, data=data)
        assert r.status_code == 400

    def test_upload_style_overwrite(self):
        """重複上傳同名樣式應成功（先刪除再建立）。"""
        sld_content = make_sld(TEST_STYLE)
        files = {
            "file": (
                f"{TEST_STYLE}.sld",
                sld_content.encode("utf-8"),
                "application/xml",
            )
        }
        data = {"style_name": TEST_STYLE}

        r = client.post("/styles", files=files, data=data)
        assert r.status_code == 200, f"覆寫樣式失敗: {r.text}"

    def test_delete_style(self):
        """刪除樣式後應從列表中消失。"""
        temp_style = "temp_delete_test_style"
        sld_content = make_sld(temp_style)
        files = {
            "file": (
                f"{temp_style}.sld",
                sld_content.encode("utf-8"),
                "application/xml",
            )
        }
        client.post("/styles", files=files, data={"style_name": temp_style})

        r = client.delete(f"/styles/{temp_style}")
        assert r.status_code == 200

        r = client.get("/styles")
        assert temp_style not in r.json()["styles"]


# ===========================================================================
# Layer 刪除
# ===========================================================================


class TestDeleteLayer:
    def test_delete_shp_layer_only(self):
        """DELETE /layers/{layer} 應僅刪除圖層，Store 保留。"""
        r = client.delete(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_SHP}/layers/{TEST_LAYER_SHP}"
        )
        assert r.status_code == 200, f"刪除 SHP 圖層失敗: {r.text}"

    def test_shp_layer_gone_after_delete(self):
        """刪除後圖層不應出現在工作區列表中。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/layers")
        layers = r.json()["layers"]
        assert TEST_LAYER_SHP not in layers

    def test_shp_store_remains_after_layer_delete(self):
        """刪除 Layer 後 Store 應保留（delete_layer 不刪除 Store）。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/stores")
        assert r.status_code == 200
        store_names = [s["name"] for s in r.json()["stores"]]
        assert TEST_STORE_SHP in store_names, (
            f"Store {TEST_STORE_SHP} 不應被 delete_layer 刪除，但已消失。"
            f" 現有 stores: {store_names}"
        )

    def test_delete_shp_store(self):
        """DELETE /stores/{store} 應刪除 Store。"""
        r = client.delete(f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_SHP}")
        assert r.status_code == 200, f"刪除 Store 失敗: {r.text}"

    def test_shp_store_gone_after_store_delete(self):
        """刪除 Store 後不應出現在工作區 Store 列表中。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/stores")
        store_names = [s["name"] for s in r.json()["stores"]]
        assert TEST_STORE_SHP not in store_names

    def test_delete_tiff_dataset(self):
        """DELETE /layers/{layer}/dataset 應同時刪除 Layer 與 Store。"""
        r = client.delete(
            f"/workspaces/{TEST_WORKSPACE}/stores/{TEST_STORE_TIFF}"
            f"/layers/{TEST_LAYER_TIFF}/dataset"
        )
        assert r.status_code == 200, f"刪除資料集失敗: {r.text}"

    def test_tiff_layer_gone_after_dataset_delete(self):
        """delete_dataset 後 Raster Layer 不應出現在工作區列表中。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/layers")
        layers = r.json()["layers"]
        assert TEST_LAYER_TIFF not in layers

    def test_tiff_store_gone_after_dataset_delete(self):
        """delete_dataset 後 CoverageStore 也不應出現在工作區 Store 列表中。"""
        r = client.get(f"/workspaces/{TEST_WORKSPACE}/stores")
        store_names = [s["name"] for s in r.json()["stores"]]
        assert TEST_STORE_TIFF not in store_names


# ===========================================================================
# 共享目錄管理
# ===========================================================================


class TestAdminEndpoints:
    def test_clear_layer_dir_nonexistent(self):
        """清理不存在的圖層目錄應回傳成功（idempotent）。"""
        r = client.delete(
            f"/admin/layer-dir/{TEST_WORKSPACE}/nonexistent_store/nonexistent_layer"
        )
        assert r.status_code == 200
