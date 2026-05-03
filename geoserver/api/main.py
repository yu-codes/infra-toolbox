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

from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from config import settings
from geoserverClient import GeoserverClient, GeoserverException

# ---------------------------------------------------------------------------
# FastAPI 應用程式初始化
# ---------------------------------------------------------------------------

app = FastAPI(
    title="GeoServer 管理 API",
    description=(
        "透過 GeoServer REST API 管理 Workspace、Layer（Vector/Raster）、Style。\n\n"
        "共享目錄結構（新方法）：`shared_dir/{workspace}/{layer_name}_store/{layer_name}/`"
    ),
    version="1.0.0",
)


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
    tags=["Workspace"],
    summary="列出工作區圖層",
)
async def list_workspace_layers(workspace: str):
    """取得指定工作區下所有圖層名稱。"""
    client = get_client()
    layers = client.get_workspace_layers(workspace)
    return {"workspace": workspace, "layers": layers}


# ===========================================================================
# Layer 管理端點
# ===========================================================================


@app.post(
    "/layers/shp",
    tags=["Layer - Vector"],
    summary="上傳 Shapefile 圖層（分散檔案）",
    response_description="建立成功訊息",
)
async def upload_shp(
    workspace: str = Form(..., description="目標工作區（需已存在）"),
    store_name: str = Form(..., description="DataStore 名稱"),
    layer_name: str = Form(..., description="圖層名稱"),
    files: List[UploadFile] = File(
        ..., description="Shapefile 組件：.shp、.shx、.dbf、.prj"
    ),
):
    """
    上傳分散的 Shapefile 組件（.shp / .shx / .dbf / .prj）並發布圖層。

    - 儲存至 `shared_dir/` 扁平結構
    - 對應 `upload_layer_shp`（既有行為不變）
    """
    client = get_client()
    result = await client.upload_layer_shp(workspace, store_name, layer_name, files)
    return {"message": result}


@app.post(
    "/layers/shp-zip",
    tags=["Layer - Vector"],
    summary="上傳 Shapefile ZIP 圖層",
    response_description="圖層資訊與服務 URL",
)
async def upload_shp_zip(
    workspace: str = Form(..., description="目標工作區（需已存在）"),
    layer_name: str = Form(
        ..., description="圖層名稱（同時作為 store 前綴與檔案基底名稱）"
    ),
    file: UploadFile = File(..., description="ZIP 壓縮檔，內含 .shp/.shx/.dbf/.prj"),
):
    """
    上傳包含完整 Shapefile 的 ZIP 並發布圖層。

    - ZIP 必須包含：`.shp`、`.shx`、`.dbf`、`.prj`
    - Store 自動命名為 `{layer_name}_store`
    - 儲存路徑：`shared_dir/{workspace}/{layer_name}_store/{layer_name}/`
    - 回傳 WMS / WFS URL
    """
    client = get_client()
    result = await client.upload_layer_shp_zip(workspace, layer_name, file)
    return result


@app.post(
    "/layers/tiff",
    tags=["Layer - Raster"],
    summary="上傳 GeoTIFF 圖層",
    response_description="圖層資訊與服務 URL",
)
async def upload_tiff(
    workspace: str = Form(..., description="目標工作區（需已存在）"),
    layer_name: str = Form(
        ..., description="圖層名稱（同時作為 store 前綴與檔案基底名稱）"
    ),
    file: UploadFile = File(..., description="GeoTIFF 檔案（.tif 或 .tiff）"),
):
    """
    上傳 GeoTIFF 並以 Coverage Store 發布 Raster Layer。

    - 支援 `.tif` / `.tiff`
    - Store 自動命名為 `{layer_name}_store`
    - 儲存路徑：`shared_dir/{workspace}/{layer_name}_store/{layer_name}/`
    - 回傳 WMS / WCS URL
    """
    client = get_client()
    result = await client.upload_layer_tiff(workspace, layer_name, file)
    return result


@app.delete(
    "/layers/{workspace}/{layer_name}",
    tags=["Layer - Vector", "Layer - Raster"],
    summary="刪除圖層",
    response_description="刪除成功訊息",
)
async def delete_layer(workspace: str, layer_name: str):
    """刪除指定工作區下的圖層（遞迴刪除關聯的 store）。"""
    client = get_client()
    result = client.delete_layer(layer_name, workspace)
    return {"message": result}


@app.get(
    "/layers/{workspace}/{layer_name}/wfs-url",
    tags=["Layer - Vector"],
    summary="取得 WFS GetFeature URL",
)
async def get_wfs_url(workspace: str, layer_name: str):
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
    "/layers/{workspace}/{layer_name}/style",
    tags=["Style"],
    summary="設定圖層預設樣式",
    response_description="設定成功訊息",
)
async def publish_style(
    workspace: str,
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
    "/admin/shared-dir",
    tags=["Admin"],
    summary="清理共享目錄（扁平結構）",
    response_description="清理成功訊息",
)
async def clear_shared_dir(base_filename: Optional[str] = None):
    """
    清理共享目錄根層級的扁平結構檔案（對應 upload_layer_shp 使用的舊結構）。

    - 若指定 base_filename，刪除 `{base_filename}.*` 所有副檔名檔案
    - 若未指定，刪除根目錄下所有直接子檔案（不含子目錄）
    """
    client = get_client()
    result = client.clear_shared_directory(base_filename)
    return {"message": result}


@app.delete(
    "/admin/layer-dir/{workspace}/{layer_name}",
    tags=["Admin"],
    summary="清理圖層目錄（新目錄結構）",
    response_description="清理成功訊息",
)
async def clear_layer_dir(workspace: str, layer_name: str):
    """
    清理新目錄結構下的圖層資料夾。

    刪除 `shared_dir/{workspace}/{layer_name}_store/{layer_name}/` 整個目錄。
    """
    client = get_client()
    result = client.clear_layer_directory(workspace, layer_name)
    return {"message": result}


# ---------------------------------------------------------------------------
# 健康檢查
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"], summary="健康檢查")
async def health_check():
    """確認 API 服務是否正常運行。"""
    return {"status": "ok", "service": "geoserver-api"}
