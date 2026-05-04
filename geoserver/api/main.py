"""
GeoServer 管理 FastAPI 應用程式

涵蓋所有 GeoserverClient 功能：
  - Workspace 管理
  - Vector Layer 上傳（Shapefile 分散 / ZIP / SHP ZIP）
  - Raster Layer 上傳（GeoTIFF）
  - Style 管理
  - 服務 URL 查詢
  - 共享目錄管理
"""

from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from geoserverClient import GeoserverClient, GeoserverException

# ---------------------------------------------------------------------------
# FastAPI 應用程式初始化
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GeoServer 管理 API",
    description=(
        "透過 GeoServer REST API 管理 Workspace、Store、Layer（Vector/Raster）、Style。\n\n"
        "三層資源結構：`Workspace → Store → Layer`\n\n"
        "Tag 說明：\n"
        "- **Workspace** — 工作區 CRUD\n"
        "- **Store** — Store 查詢 / 刪除\n"
        "- **Layer** — 圖層列表 / 刪除（格式無關）\n"
        "- **Layer / Vector** — Shapefile ZIP 上傳、WFS URL\n"
        "- **Layer / Raster** — GeoTIFF 上傳\n"
        "- **Style** — 樣式管理\n"
        "- **Admin** — 備份目錄維護"
    ),
    version="2.0.0",
    openapi_tags=[
        {"name": "Workspace"},
        {"name": "Store"},
        {"name": "Layer"},
        {"name": "Layer / Vector"},
        {"name": "Layer / Raster"},
        {"name": "Style"},
        {"name": "Admin"},
        {"name": "Health"},
    ],
)

# 掛載前端靜態檔案（index.html 等）
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# 依賴注入：每個請求產生一個 GeoserverClient 實例
# ---------------------------------------------------------------------------


def get_client() -> GeoserverClient:
    return GeoserverClient(
        service_url=settings.geoserver_url,
        username=settings.geoserver_username,
        password=settings.geoserver_password,
        shared_dir=settings.shared_dir,
    )


# ---------------------------------------------------------------------------
# 全域例外處理：GeoserverException → HTTP 回應
# ---------------------------------------------------------------------------


@app.exception_handler(GeoserverException)
async def geoserver_exception_handler(request, exc: GeoserverException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


# ===========================================================================
# Workspace 管理端點
# ===========================================================================


@app.post(
    "/workspaces",
    tags=["Workspace"],
    summary="建立工作區",
    response_description="建立成功訊息",
)
async def create_workspace(workspace: str = Form(..., description="工作區名稱")):
    """建立一個新的 GeoServer 工作區。"""
    client = get_client()
    result = client.create_workspace(workspace)
    return {"message": result}


@app.get(
    "/workspaces",
    tags=["Workspace"],
    summary="列出所有工作區",
)
async def list_workspaces():
    """取得所有已存在的工作區名稱列表。"""
    client = get_client()
    workspaces = client.get_workspaces()
    return {"workspaces": workspaces}


@app.delete(
    "/workspaces/{workspace}",
    tags=["Workspace"],
    summary="刪除工作區",
    response_description="刪除成功訊息",
)
async def delete_workspace(workspace: str):
    """刪除指定工作區及其下所有資源（遞迴刪除）。"""
    client = get_client()
    result = client.delete_workspace(workspace)
    return {"message": result}


@app.get(
    "/workspaces/{workspace}/layers",
    tags=["Layer"],
    summary="列出工作區圖層",
)
async def list_workspace_layers(workspace: str):
    """取得指定工作區下所有圖層名稱。"""
    client = get_client()
    layers = client.get_workspace_layers(workspace)
    return {"workspace": workspace, "layers": layers}


@app.get(
    "/workspaces/{workspace}/stores",
    tags=["Store"],
    summary="列出工作區的所有 Store",
)
async def list_workspace_stores(workspace: str):
    """
    取得工作區下所有 Store（Datastore + CoverageStore）與其類型。

    回傳格式：
      {"workspace": "demo", "stores": [{"name": "my_store", "type": "vector"}, ...]}
    """
    client = get_client()
    stores = client.get_workspace_stores(workspace)
    return {"workspace": workspace, "stores": stores}


# ===========================================================================
# Layer 管理端點（三層結構： workspace → store → layer）
# ===========================================================================


@app.post(
    "/workspaces/{workspace}/stores/{store_name}/layers/shp-zip",
    tags=["Layer / Vector"],
    summary="上傳 Shapefile ZIP 圖層",
    response_description="圖層資訊與服務 URL",
)
async def upload_shp_zip(
    workspace: str,
    store_name: str,
    layer_name: str = Form(..., description="圖層名稱（同時作為檔案基底名稱）"),
    file: UploadFile = File(..., description="ZIP 壓縮檔，內含 .shp/.shx/.dbf/.prj"),
):
    """
    上傳包含完整 Shapefile 的 ZIP 並發布圖層。

    - ZIP 必須包含：`.shp`、`.shx`、`.dbf`、`.prj`
    - 儲存路徑：`shared_dir/{workspace}/{store_name}/{layer_name}/`
    - 回傳 WMS / WFS URL
    """
    client = get_client()
    result = await client.upload_layer_shp_zip(
        workspace, layer_name, file, store_name=store_name
    )
    return result


@app.post(
    "/workspaces/{workspace}/stores/{store_name}/layers/tiff",
    tags=["Layer / Raster"],
    summary="上傳 GeoTIFF 圖層",
    response_description="圖層資訊與服務 URL",
)
async def upload_tiff(
    workspace: str,
    store_name: str,
    layer_name: str = Form(..., description="圖層名稱（同時作為檔案基底名稱）"),
    file: UploadFile = File(..., description="GeoTIFF 檔案（.tif 或 .tiff）"),
):
    """
    上傳 GeoTIFF 並以 Coverage Store 發布 Raster Layer。

    - 支援 `.tif` / `.tiff`
    - 儲存路徑：`shared_dir/{workspace}/{store_name}/{layer_name}/`
    - 回傳 WMS / WCS URL
    """
    client = get_client()
    result = await client.upload_layer_tiff(
        workspace, layer_name, file, store_name=store_name
    )
    return result


@app.delete(
    "/workspaces/{workspace}/stores/{store_name}/layers/{layer_name}",
    tags=["Layer"],
    summary="刪除圖層（保留 Store）",
    response_description="刪除成功訊息",
)
async def delete_layer(workspace: str, store_name: str, layer_name: str):
    """
    僅刪除指定圖層，Store 保留。

    適用於 Multi-Layer Store 情境：刪除其中一個 Layer，不影響同一 Store
    下的其他 Layer。

    若要同時刪除 Layer 與 Store（Dataset 策略），請使用：
    `DELETE /workspaces/{workspace}/stores/{store_name}/layers/{layer_name}/dataset`
    """
    client = get_client()
    result = client.delete_layer(workspace, layer_name, store_name=store_name)
    return {"message": result}


@app.delete(
    "/workspaces/{workspace}/stores/{store_name}",
    tags=["Store"],
    summary="刪除 Store（遞迴刪除其下所有 Layer）",
    response_description="刪除成功訊息",
)
async def delete_store(
    workspace: str,
    store_name: str,
    store_type: str = "datastore",
):
    """
    刪除指定 Store 及其下所有 Layer（遞迴刪除）。

    - `store_type=datastore`（預設）：向量 Store
    - `store_type=coveragestore`：柵格 Store

    若只要刪除單一 Layer 而保留 Store，請使用：
    `DELETE /workspaces/{workspace}/stores/{store_name}/layers/{layer_name}`
    """
    client = get_client()
    result = client.delete_store(workspace, store_name, store_type=store_type)
    return {"message": result}


@app.delete(
    "/workspaces/{workspace}/stores/{store_name}/layers/{layer_name}/dataset",
    tags=["Layer"],
    summary="刪除資料集（Layer + Store 一併刪除）",
    response_description="刪除成功訊息",
)
async def delete_dataset(workspace: str, store_name: str, layer_name: str):
    """
    同時刪除 Layer 與其專屬 Store（Dataset 策略的一起刪除）。

    專用於 1:1 Dataset 策略場景，資料集與接入點同步消失。
    若 Store 下尚有其他 Layer，請改用：
    `DELETE /workspaces/{workspace}/stores/{store_name}/layers/{layer_name}`
    """
    client = get_client()
    result = client.delete_dataset(workspace, store_name, layer_name)
    return {"message": result}


@app.get(
    "/workspaces/{workspace}/stores/{store_name}/layers/{layer_name}/wfs-url",
    tags=["Layer / Vector"],
    summary="取得 WFS GetFeature URL",
)
async def get_wfs_url(workspace: str, store_name: str, layer_name: str):
    """取得圖層的 WFS GetFeature 請求 URL（GeoJSON 格式）。"""
    client = get_client()
    url = client.get_layer_wfs_url(layer_name, workspace)
    return {"wfs_url": url}


# ===========================================================================
# Style 管理端點
# ===========================================================================


@app.post(
    "/styles",
    tags=["Style"],
    summary="上傳 SLD 樣式",
    response_description="上傳成功訊息",
)
async def upload_style(
    style_name: str = Form(..., description="樣式名稱"),
    file: UploadFile = File(..., description="SLD 檔案（.sld）"),
    workspace: Optional[str] = Form(default=None, description="[可選] 工作區名稱"),
):
    """上傳 SLD 樣式（若已存在會先刪除再重新上傳）。"""
    client = get_client()
    result = await client.upload_style(style_name, file, workspace)
    return {"message": result}


@app.get(
    "/styles",
    tags=["Style"],
    summary="列出樣式",
)
async def list_styles(workspace: Optional[str] = None):
    """取得樣式名稱列表。可傳入 workspace 查詢工作區樣式，否則查詢全域樣式。"""
    client = get_client()
    styles = client.get_workspace_styles(workspace)
    return {"workspace": workspace, "styles": styles}


@app.put(
    "/workspaces/{workspace}/stores/{store_name}/layers/{layer_name}/style",
    tags=["Style"],
    summary="設定圖層預設樣式",
    response_description="設定成功訊息",
)
async def publish_style(
    workspace: str,
    store_name: str,
    layer_name: str,
    style_name: str = Form(..., description="要套用的樣式名稱"),
):
    """將指定樣式設為圖層的預設樣式。"""
    client = get_client()
    result = client.publish_style(layer_name, style_name, workspace)
    return {"message": result}


@app.delete(
    "/styles/{style_name}",
    tags=["Style"],
    summary="刪除樣式",
    response_description="刪除成功訊息",
)
async def delete_style(
    style_name: str,
    workspace: Optional[str] = None,
    purge: bool = True,
    recurse: bool = True,
):
    """刪除指定樣式。purge=true 時同時刪除 SLD 檔案；recurse=true 時強制刪除（即使被使用中）。"""
    client = get_client()
    result = client.delete_style(style_name, workspace, purge, recurse)
    return {"message": result}


# ===========================================================================
# 管理端點
# ===========================================================================


@app.delete(
    "/admin/layer-dir/{workspace}/{store_name}/{layer_name}",
    tags=["Admin"],
    summary="清理圖層目錄",
    response_description="清理成功訊息",
)
async def clear_layer_dir(workspace: str, store_name: str, layer_name: str):
    """
    清理三層目錄結構下的圖層資料夾。

    刪除 `shared_dir/{workspace}/{store_name}/{layer_name}/` 整個目錄。
    """
    client = get_client()
    result = client.clear_layer_directory(workspace, store_name, layer_name)
    return {"message": result}


# ---------------------------------------------------------------------------
# 前端入口
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """提供前端管理介面（index.html）。"""
    response = FileResponse("static/index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ---------------------------------------------------------------------------
# 健康檢查
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"], summary="健康檢查")
async def health_check():
    """確認 API 服務是否正常運行。"""
    return {"status": "ok", "service": "geoserver-api"}


# ---------------------------------------------------------------------------
# 圖層聚合（供前端使用）
# ---------------------------------------------------------------------------


@app.get(
    "/layers",
    tags=["Layer"],
    summary="列出所有工作區的圖層",
)
async def list_all_layers():
    """
    取得所有工作區的所有圖層（含 workspace 資訊），供前端地圖面板使用。

    回傳格式：
      {"layers": [{"workspace": "demo", "layer": "taiwan_grid", "type": "vector"}, ...]}
    """
    client = get_client()
    try:
        workspaces = client.get_workspaces()
    except GeoserverException:
        return {"layers": []}

    result = []
    for ws in workspaces:
        try:
            layers = client.get_workspace_layers(ws)
            datastores = set(client.get_workspace_datastores(ws))
            coveragestores = set(client.get_workspace_coveragestores(ws))
            for layer in layers:
                store_name = f"{layer}_store"
                if store_name in coveragestores:
                    layer_type = "raster"
                elif store_name in datastores:
                    layer_type = "vector"
                else:
                    # Fallback: substring match when naming convention differs
                    raster_match = next((s for s in coveragestores if layer in s), None)
                    vector_match = next((s for s in datastores if layer in s), None)
                    if raster_match:
                        store_name = raster_match
                        layer_type = "raster"
                    elif vector_match:
                        store_name = vector_match
                        layer_type = "vector"
                    else:
                        layer_type = "vector"  # last-resort default
                result.append(
                    {
                        "workspace": ws,
                        "layer": layer,
                        "type": layer_type,
                        "store": store_name,
                    }
                )
        except GeoserverException:
            continue
    return {"layers": result}
