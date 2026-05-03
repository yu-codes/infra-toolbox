"""
GeoserverClient - GeoServer REST API 封裝模組

支援功能：
  - Workspace 管理（建立、刪除、查詢）
  - Vector Layer 管理（Shapefile 分散上傳、ZIP 上傳）
  - Raster Layer 管理（GeoTIFF 上傳）
  - Style 管理（SLD 上傳、套用、刪除）
  - 共享目錄管理

目錄結構慣例（新方法）：
  shared_dir/
    └── {workspace}/
        └── {layer_name}_store/
            └── {layer_name}/
                ├── *.shp / *.shx / *.dbf / *.prj  (vector)
                └── *.tif / *.tiff                  (raster)
"""

import io
import zipfile
import requests
from pathlib import Path
from typing import Optional, List

from fastapi import UploadFile

# ---------------------------------------------------------------------------
# 例外類別
# ---------------------------------------------------------------------------


class GeoserverException(Exception):
    """GeoServer 操作例外，包含 HTTP 狀態碼與錯誤訊息。"""

    def __init__(self, status_code: int, message):
        self.status_code = status_code
        # 相容 bytes 與 str 兩種訊息格式
        self.message = (
            message.decode("utf-8", errors="replace")
            if isinstance(message, bytes)
            else str(message)
        )
        super().__init__(f"status: {status_code}, message: {self.message}")


class GeoserverClient:
    def __init__(self, service_url: str, username: str, password: str, shared_dir: str):
        """
        初始化 GeoserverClient

        Args:
            service_url: GeoServer 服務根 URL（例如 http://localhost:8080/geoserver）
            username:    GeoServer 管理員帳號
            password:    GeoServer 管理員密碼
            shared_dir:  與 GeoServer 容器共享的目錄路徑（兩端路徑必須一致）
        """
        self.service_url = service_url.rstrip("/")
        self.username = username
        self.password = password
        self.shared_dir = shared_dir

    def create_workspace(self, workspace: str) -> str:
        """
        建立 GeoServer 工作區。

        REST: POST /rest/workspaces
        Body: XML <workspace><name>...</name></workspace>
        """
        url = f"{self.service_url}/rest/workspaces"
        data = f"<workspace><name>{workspace}</name></workspace>".encode("utf-8")
        headers = {"content-type": "text/xml; charset=utf-8"}
        r = requests.post(
            url, auth=(self.username, self.password), data=data, headers=headers
        )
        if r.status_code == 201:
            return f"工作區 {workspace} 建立成功"
        raise GeoserverException(r.status_code, r.content)

    def delete_workspace(self, workspace: str) -> str:
        """
        刪除指定工作區（遞迴刪除其下所有資源）。

        REST: DELETE /rest/workspaces/{workspace}?recurse=true
        """
        url = f"{self.service_url}/rest/workspaces/{workspace}"
        params = {"recurse": "true"}  # 遞歸刪除工作區中的所有資源
        r = requests.delete(url, auth=(self.username, self.password), params=params)
        if r.status_code == 200:
            return f"工作區 {workspace} 刪除成功"
        raise GeoserverException(r.status_code, r.content)

    def get_workspaces(self) -> List[str]:
        """
        取得所有工作區名稱列表。

        REST: GET /rest/workspaces.json
        """
        url = f"{self.service_url}/rest/workspaces.json"
        r = requests.get(url, auth=(self.username, self.password))
        if r.status_code == 200:
            response_json = r.json()
            if "workspaces" in response_json and response_json["workspaces"]:
                workspaces = response_json["workspaces"].get("workspace", [])
                return [workspace["name"] for workspace in workspaces]
            return []
        raise GeoserverException(r.status_code, r.content)

    def get_workspace_layers(self, workspace: str) -> List[str]:
        """
        取得指定工作區下的所有圖層名稱。

        REST: GET /rest/workspaces/{workspace}/layers
        """
        url = f"{self.service_url}/rest/workspaces/{workspace}/layers"
        r = requests.get(url, auth=(self.username, self.password))
        if r.status_code == 200:
            response_json = r.json()
            if "layers" in response_json and response_json["layers"]:
                layers = response_json["layers"].get("layer", [])
                return [str(layer["name"]) for layer in layers]
            return []
        raise GeoserverException(r.status_code, r.content)

    async def upload_layer_shp(
        self, workspace: str, store_name: str, layer_name: str, files: List[UploadFile]
    ) -> str:
        """
        上傳並發布 Shapefile 圖層（接受分散的 .shp/.shx/.dbf/.prj 檔案）。

        行為：
          - 儲存至 shared_dir/（扁平結構，保留既有設計，不修改行為）
          - 以 layer_name 作為基礎檔名重新命名
          - 驗證必要組件齊全後呼叫 GeoServer API

        REST: PUT /rest/workspaces/{ws}/datastores/{ds}/external.shp
          params: configure=all, charset=UTF-8, update=overwrite
        """
        # 將 UploadFile (臨時儲存的上傳文件) 保存到實際的共享目錄中
        upload_dir = Path(self.shared_dir)
        for file in files:
            extension = Path(file.filename).suffix.lower()
            new_filename = f"{layer_name}{extension}"  # 以 layer_name 作為新檔案名稱
            file_path = upload_dir / new_filename
            with file_path.open("wb") as buffer:
                content = await file.read()
                buffer.write(content)
        # 檢查 shapefile 的必要文件是否存在
        required_extensions = [".shp", ".shx", ".dbf", ".prj"]
        for ext in required_extensions:
            if not (upload_dir / f"{layer_name}{ext}").exists():
                raise GeoserverException(400, f"缺少必要文件: {layer_name}{ext}")
        # 透過 .shp 發布圖層
        shp_path = str(upload_dir / f"{layer_name}.shp")
        url = f"{self.service_url}/rest/workspaces/{workspace}/datastores/{store_name}/external.shp"
        headers = {"Content-type": "text/plain; charset=utf-8"}
        params = {"configure": "all", "charset": "UTF-8", "update": "overwrite"}
        r = requests.put(
            url,
            auth=(self.username, self.password),
            data=shp_path.encode("utf-8"),
            headers=headers,
            params=params,
        )
        if r.status_code in (200, 201):
            return f"圖層 {layer_name} 建立成功"
        raise GeoserverException(r.status_code, r.content)

    async def upload_layer_shp_zip(
        self, workspace: str, layer_name: str, file: UploadFile
    ) -> dict:
        """
        上傳 ZIP 格式 Shapefile 並發布 Vector Layer。

        ZIP 必須包含完整 Shapefile 組件：.shp、.shx、.dbf、.prj
        目錄結構：shared_dir/{workspace}/{layer_name}_store/{layer_name}/

        GeoServer REST API：
          PUT /rest/workspaces/{ws}/datastores/{ds}/external.shp
          Content-Type: text/plain
          Body: file:///path/to/{layer_name}.shp（GeoServer 容器內的絕對路徑）
          Params: configure=all, charset=UTF-8, update=overwrite

        命名規則：
          - workspace 由呼叫端傳入，不存在時 GeoServer 會回傳錯誤
          - store 命名為 {layer_name}_store，若已存在則重用
          - 解壓後以 layer_name 統一命名，原 ZIP 不保留

        Returns:
            dict: workspace / store / layer / data_type / service_urls
        """
        if not file.filename.lower().endswith(".zip"):
            raise GeoserverException(400, "僅支援 .zip 格式的 Shapefile 壓縮包")

        store_name = f"{layer_name}_store"

        # 建立標準化目錄結構
        target_dir = Path(self.shared_dir) / workspace / store_name / layer_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # 讀取並解壓 ZIP，以 layer_name 重新命名各組件
        content = await file.read()
        required_exts = {".shp", ".shx", ".dbf", ".prj"}
        found_exts: set = set()

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    ext = Path(name).suffix.lower()
                    if ext in required_exts:
                        found_exts.add(ext)
                        target_file = target_dir / f"{layer_name}{ext}"
                        target_file.write_bytes(zf.read(name))
        except zipfile.BadZipFile:
            raise GeoserverException(400, "無效的 ZIP 檔案格式")

        # 驗證必要組件是否齊全
        missing = required_exts - found_exts
        if missing:
            raise GeoserverException(
                400, f"ZIP 缺少必要的 Shapefile 組件: {sorted(missing)}"
            )

        # 使用 Path.as_uri() 產生 file:// URI（GeoServer 需透過此路徑存取容器內的檔案）
        # 例: /shared/ws/store/layer/layer.shp → file:///shared/ws/store/layer/layer.shp
        shp_file = target_dir / f"{layer_name}.shp"
        shp_uri = shp_file.as_uri()

        # 呼叫 GeoServer external.shp API 發布 Vector Layer
        url = f"{self.service_url}/rest/workspaces/{workspace}/datastores/{store_name}/external.shp"
        headers = {"Content-type": "text/plain; charset=utf-8"}
        params = {"configure": "all", "charset": "UTF-8", "update": "overwrite"}
        r = requests.put(
            url,
            auth=(self.username, self.password),
            data=shp_uri.encode("utf-8"),
            headers=headers,
            params=params,
        )
        if r.status_code not in (200, 201):
            raise GeoserverException(r.status_code, r.text)

        return {
            "workspace": workspace,
            "store": store_name,
            "layer": layer_name,
            "data_type": "vector",
            "service_urls": {
                "wms": (
                    f"{self.service_url}/{workspace}/wms"
                    f"?service=WMS&version=1.1.0&request=GetMap"
                    f"&layers={workspace}:{layer_name}"
                    f"&bbox=-180,-90,180,90&width=256&height=256"
                    f"&srs=EPSG:4326&format=image/png"
                ),
                "wfs": self.get_layer_wfs_url(layer_name, workspace),
            },
        }

    async def upload_layer_tiff(
        self, workspace: str, layer_name: str, file: UploadFile
    ) -> dict:
        """
        上傳 GeoTIFF 並以 Coverage Store 發布 Raster Layer。

        支援副檔名：.tif、.tiff
        目錄結構：shared_dir/{workspace}/{layer_name}_store/{layer_name}/

        GeoServer REST API：
          PUT /rest/workspaces/{ws}/coveragestores/{cs}/external.geotiff
          Content-Type: text/plain
          Body: file:///path/to/{layer_name}.tif（GeoServer 容器內的絕對路徑）
          Params: configure=all, update=overwrite

        命名規則：
          - coverage store 命名為 {layer_name}_store（與 vector 統一規則）
          - REST 路徑使用 coveragestores（非 datastores）
          - 不嘗試轉檔，不依賴 PostGIS

        Returns:
            dict: workspace / store / layer / data_type / service_urls
        """
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith(".tif") or filename_lower.endswith(".tiff")):
            raise GeoserverException(400, "僅支援 .tif 或 .tiff 格式")

        store_name = f"{layer_name}_store"
        ext = Path(file.filename).suffix.lower()

        # 建立標準化目錄結構
        target_dir = Path(self.shared_dir) / workspace / store_name / layer_name
        target_dir.mkdir(parents=True, exist_ok=True)

        # 儲存 GeoTIFF，以 layer_name 重新命名
        target_file = target_dir / f"{layer_name}{ext}"
        content = await file.read()
        target_file.write_bytes(content)

        # 使用 Path.as_uri() 產生 file:// URI
        # 例: /shared/ws/store/layer/layer.tif → file:///shared/ws/store/layer/layer.tif
        tif_uri = target_file.as_uri()

        # 呼叫 GeoServer external.geotiff API 發布 Coverage Layer
        # 注意：raster 使用 coveragestores，vector 使用 datastores
        url = (
            f"{self.service_url}/rest/workspaces/{workspace}"
            f"/coveragestores/{store_name}/external.geotiff"
        )
        headers = {"Content-type": "text/plain; charset=utf-8"}
        params = {"configure": "all", "update": "overwrite"}
        r = requests.put(
            url,
            auth=(self.username, self.password),
            data=tif_uri.encode("utf-8"),
            headers=headers,
            params=params,
        )
        if r.status_code not in (200, 201):
            raise GeoserverException(r.status_code, r.text)

        return {
            "workspace": workspace,
            "store": store_name,
            "layer": layer_name,
            "data_type": "raster",
            "service_urls": {
                "wms": (
                    f"{self.service_url}/{workspace}/wms"
                    f"?service=WMS&version=1.1.0&request=GetMap"
                    f"&layers={workspace}:{layer_name}"
                    f"&bbox=-180,-90,180,90&width=256&height=256"
                    f"&srs=EPSG:4326&format=image/png"
                ),
                "wcs": (
                    f"{self.service_url}/{workspace}/wcs"
                    f"?service=WCS&version=2.0.1&request=DescribeCoverage"
                    f"&coverageId={workspace}__{layer_name}"
                ),
            },
        }

    def delete_layer(self, layer_name: str, workspace: Optional[str] = None) -> str:
        """
        刪除指定圖層（遞迴刪除關聯的 store）並清理共享目錄中的扁平結構檔案。

        REST: DELETE /rest/workspaces/{ws}/layers/{layer}?recurse=true
        """
        if workspace:
            url = f"{self.service_url}/rest/workspaces/{workspace}/layers/{layer_name}"
        else:
            url = f"{self.service_url}/rest/layers/{layer_name}"
        params = {"recurse": "true"}
        r = requests.delete(url, auth=(self.username, self.password), params=params)
        if r.status_code == 200:
            try:
                self.clear_shared_directory(layer_name)  # 刪除共享目錄中的相關檔案
            except Exception as e:
                return f"圖層 {layer_name} 刪除成功，但清除共享目錄檔案失敗: {str(e)}"
            return f"圖層 {layer_name} 刪除成功"
        raise GeoserverException(r.status_code, r.content)

    async def upload_style(
        self, style_name: str, file: UploadFile, workspace: Optional[str] = None
    ) -> str:
        """
        上傳 SLD 樣式（若已存在則先刪除再上傳）。

        REST:
          POST /rest/workspaces/{ws}/styles  → 建立 style 條目
          PUT  /rest/workspaces/{ws}/styles/{name}  → 上傳 SLD 內容（Content-Type: vnd.ogc.se+xml）
        """
        # 檢查檔案格式
        extension = Path(file.filename).suffix.lower()
        if extension != ".sld":
            raise GeoserverException(
                400, f"不支援的檔案格式: {extension}，僅支援.sld檔案"
            )
        # 先嘗試刪除已存在的樣式
        try:
            self.delete_style(style_name, workspace, purge=True, recurse=True)
        except:
            pass
        # 讀取 SLD 檔案的內容
        try:
            content = await file.read()
            sld_content = content.decode("utf-8")
        except Exception as e:
            raise GeoserverException(400, f"讀取SLD檔案失敗: {str(e)}")
        # 在 GeoServer 中建立 style 條目
        if workspace:
            url = f"{self.service_url}/rest/workspaces/{workspace}/styles"
        else:
            url = f"{self.service_url}/rest/styles"
        headers = {"content-type": "text/xml; charset=utf-8"}
        data = f"<style><name>{style_name}</name><filename>{style_name}.sld</filename></style>".encode(
            "utf-8"
        )
        r = requests.post(
            url, auth=(self.username, self.password), data=data, headers=headers
        )
        if r.status_code != 201:
            raise GeoserverException(r.status_code, r.text)
        # 上傳 SLD 檔案的內容
        headers = {
            "content-type": "application/vnd.ogc.se+xml; charset=utf-8"
        }  # SLD v1.0: application/vnd.ogc.sld+xml v1.1: application/vnd.ogc.se+xml
        if workspace:
            url = f"{self.service_url}/rest/workspaces/{workspace}/styles/{style_name}"
        else:
            url = f"{self.service_url}/rest/styles/{style_name}"
        r = requests.put(
            url,
            auth=(self.username, self.password),
            data=sld_content.encode("utf-8"),
            headers=headers,
        )
        if r.status_code == 200:
            return f"樣式 {style_name} 上傳成功"
        raise GeoserverException(r.status_code, r.text)

    def publish_style(
        self, layer_name: str, style_name: str, workspace: Optional[str] = None
    ) -> str:
        """
        將指定樣式設為圖層的預設樣式。

        REST: PUT /rest/layers/{ws}:{layer}
        Body: XML <layer><defaultStyle>...</defaultStyle></layer>
        """
        if workspace:
            url = f"{self.service_url}/rest/layers/{workspace}:{layer_name}"
        else:
            url = f"{self.service_url}/rest/layers/{layer_name}"
        data = f"<layer><defaultStyle><name>{style_name}</name></defaultStyle></layer>".encode(
            "utf-8"
        )
        headers = {"content-type": "text/xml; charset=utf-8"}
        r = requests.put(
            url, auth=(self.username, self.password), data=data, headers=headers
        )
        if r.status_code == 200:
            return f"樣式 {style_name} 已設置為圖層 {layer_name} 的預設樣式"
        raise GeoserverException(r.status_code, r.content)

    def get_workspace_styles(self, workspace: Optional[str] = None) -> List[str]:
        """
        取得樣式名稱列表。

        REST: GET /rest/workspaces/{ws}/styles.json  或  GET /rest/styles.json
        """
        if workspace:
            url = f"{self.service_url}/rest/workspaces/{workspace}/styles.json"
        else:
            url = f"{self.service_url}/rest/styles.json"

        r = requests.get(url, auth=(self.username, self.password))
        if r.status_code == 200:
            styles = r.json().get("styles", {}).get("style", [])
            return [style["name"] for style in styles]
        raise GeoserverException(r.status_code, r.content)

    def delete_style(
        self,
        style_name: str,
        workspace: Optional[str] = None,
        purge: bool = True,
        recurse: bool = True,
    ) -> str:
        """
        刪除指定樣式。

        Args:
            purge:   True = 連同 SLD 檔案一起刪除；False = 僅刪除 style 條目
            recurse: True = 強制刪除（即使仍被 layer 使用）
        """
        if workspace:
            url = f"{self.service_url}/rest/workspaces/{workspace}/styles/{style_name}"
        else:
            url = f"{self.service_url}/rest/styles/{style_name}"
        params = {"purge": str(purge).lower(), "recurse": str(recurse).lower()}
        r = requests.delete(url, auth=(self.username, self.password), params=params)
        if r.status_code == 200:
            return f"樣式 {style_name} 刪除成功"
        raise GeoserverException(r.status_code, r.content)

    def get_layer_wfs_url(self, layer_name: str, workspace: str) -> str:
        """
        產生圖層的 WFS GetFeature 請求 URL（GeoJSON 格式）。
        """
        return (
            f"{self.service_url}/wfs?"
            f"service=WFS&version=2.0.0&request=GetFeature&"
            f"typeName={workspace}:{layer_name}&"
            f"outputFormat=application/json"
        )

    def clear_shared_directory(self, base_filename: Optional[str] = None) -> str:
        """
        清理共享目錄中的扁平結構檔案（upload_layer_shp 使用的舊結構）。

        Args:
            base_filename: 若指定，刪除 shared_dir/{base_filename}.* 所有副檔名的檔案；
                           若未指定，刪除 shared_dir/ 根目錄下所有檔案（不含子目錄）。
        """
        shared_path = Path(self.shared_dir)
        if base_filename:
            for file in shared_path.glob(f"{base_filename}.*"):
                if file.is_file():
                    file.unlink()
            return f"已刪除所有 {base_filename}.* 檔案"
        else:
            for file in shared_path.glob("*"):
                if file.is_file():
                    file.unlink()
            return "共享目錄根層級已清空"

    def clear_layer_directory(self, workspace: str, layer_name: str) -> str:
        """
        清理新目錄結構下的圖層資料夾。

        刪除 shared_dir/{workspace}/{layer_name}_store/{layer_name}/ 整個目錄。
        供 upload_layer_shp_zip / upload_layer_tiff 使用的清理方法。
        """
        import shutil

        store_name = f"{layer_name}_store"
        target_dir = Path(self.shared_dir) / workspace / store_name / layer_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
            return f"已刪除圖層目錄: {target_dir}"
        return f"圖層目錄不存在，無需清理: {target_dir}"
