"""
GeoserverClient - GeoServer 發布管理模組

【模組定位】
  本模組封裝 GeoServer REST API，提供完整的 Workspace / Store / Layer
  三層資源生命週期管理，以及本地備份目錄的維護。

【GeoServer 原生資源模型】
  Workspace → Store (DataStore / CoverageStore) → Resource → Layer
    - 1 個 Store 可對應多個 Resource / Layer（GeoServer 原生支援）
    - Store 是資料來源的連線或接入點，與其上方的 Layer 為 1:N 關係

【應用層發布策略（兩種，可選）】
  A. Dataset 策略（預設）：1 Store : 1 Layer
     適用於檔案上傳場景，每個資料集有自己獨立的 Store
     store 命名慣例：{layer_name}_store
     對應參數：store_name=None, reuse_store=False（預設）

  B. Multi-Layer 策略：1 Store : N Layers
     適用於同一種套疊下多個資料集共用 Store（例如同一地區的多時期圖層）
     store 由呼叫端明確命名，電責語意由應用層負責
     對應參數：store_name="my_store", reuse_store=True

  ⚠️ 命名格式 {layer_name}_store 是慣例（Convention），不是系統強制限制。

【shared_dir 責任邊界（重要）】
  shared_dir/{workspace}/{store_name}/{layer_name}/ 的用途：
    ✅ 營運備份：保存最後一次上傳的原始檔案，供回溯核查
    ✅ Debug / 稽核：快速確認哪些資料集已發布至 GeoServer
    ❌ 非 GeoServer 真實資料來源（data_dir）
    ❌ 從此目錄刪除檔案，不影響 GeoServer 的即時服務
  ⚠️ 警告：若 GeoServer 的 dataDir 恰好位於同一掛載路徑，
          請確保兩者目錄路徑不重疊，否則刪除備份可能誤刪服務資料。

支援功能：
  - Workspace 管理（建立、刪除、查詢）
  - Store 管理（Datastore / CoverageStore 查詢、刪除）
  - Vector Layer 管理（Shapefile ZIP 上傳）
  - Raster Layer 管理（GeoTIFF 上傳）
  - Style 管理（SLD 上傳、套用、刪除）

三層資源結構（GeoServer 端）：
  Workspace  →  Store (DataStore / CoverageStore)  →  Layer

備份目錄（本地端，僅供備援稽核）：
  shared_dir/
    └── {workspace}/
        └── {store_name}/
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
    """
    GeoServer 發布管理器。

    封裝 GeoServer REST API，支援兩種發布策略：

    A. Dataset 策略（預設）：上傳檔案時自動建立專屬 Store
       store_name 略不傳時使用 {layer_name}_store 慣例命名
       upload_layer_shp_zip(workspace, layer_name, file)                # store 自動建立

    B. Multi-Layer 策略：多個 Layer 共用同一 Store
       upload_layer_shp_zip(workspace, layer_name, file,
                            store_name="shared_store", reuse_store=True) # store 重用

    命名慣例 {layer_name}_store 是 Convention，不是系統強制。

    Thread safety：本類別不持有狀態（除初始化參數外），可安全用於
    FastAPI 的 per-request 依賴注入模式。
    """

    def __init__(self, service_url: str, username: str, password: str, shared_dir: str):
        """
        初始化 GeoServer 發布管理器。

        Args:
            service_url: GeoServer 服務根 URL（例如 http://geoserver:8080/geoserver）
            username:    GeoServer 管理員帳號
            password:    GeoServer 管理員密碼
            shared_dir:  備份目錄路徑（API 容器可寫入的掛載路徑）
                         ⚠️ 此目錄僅作備援稽核用途，不是 GeoServer 的資料來源。
                            刪除此目錄中的檔案不影響 GeoServer 已發布的服務。
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

    def get_workspace_datastores(self, workspace: str) -> List[str]:
        """
        取得工作區下所有 Datastore（向量）名稱列表。

        REST: GET /rest/workspaces/{workspace}/datastores.json
        """
        url = f"{self.service_url}/rest/workspaces/{workspace}/datastores.json"
        r = requests.get(url, auth=(self.username, self.password))
        if r.status_code == 200:
            val = r.json().get("dataStores", {})
            if not isinstance(val, dict):
                return []
            stores = val.get("dataStore", [])
            if isinstance(stores, dict):
                stores = [stores]
            return [s["name"] for s in stores]
        return []

    def get_workspace_coveragestores(self, workspace: str) -> List[str]:
        """
        取得工作區下所有 CoverageStore（柵格）名稱列表。

        REST: GET /rest/workspaces/{workspace}/coveragestores.json
        """
        url = f"{self.service_url}/rest/workspaces/{workspace}/coveragestores.json"
        r = requests.get(url, auth=(self.username, self.password))
        if r.status_code == 200:
            val = r.json().get("coverageStores", {})
            if not isinstance(val, dict):
                return []
            stores = val.get("coverageStore", [])
            if isinstance(stores, dict):
                stores = [stores]
            return [s["name"] for s in stores]
        return []

    def get_workspace_stores(self, workspace: str) -> List[dict]:
        """
        取得工作區下所有 Store（Datastore + CoverageStore）名稱與類型。

        Returns:
            List[dict]: [{"name": store_name, "type": "vector" | "raster"}, ...]
        """
        result = [
            {"name": name, "type": "vector"}
            for name in self.get_workspace_datastores(workspace)
        ]
        result += [
            {"name": name, "type": "raster"}
            for name in self.get_workspace_coveragestores(workspace)
        ]
        return result

    async def upload_layer_shp_zip(
        self,
        workspace: str,
        layer_name: str,
        file: UploadFile,
        store_name: Optional[str] = None,
        reuse_store: bool = False,
    ) -> dict:
        """
        上傳 Shapefile ZIP 並發布 Vector Layer。

        支援兩種策略：

          Dataset 策略（預設，reuse_store=False）：
            upload_layer_shp_zip(ws, "my_layer", file)
            → 建立新 Store「my_layer_store」，發布 Layer「my_layer」
            → store_name 略不傳時自動產生 {layer_name}_store

          Multi-Layer 策略（reuse_store=True）：
            upload_layer_shp_zip(ws, "q2_layer", file,
                                 store_name="quarterly_store", reuse_store=True)
            → 重用已存在的 Store「quarterly_store」
            → Store 必須已建立，否則 GeoServer 會回傳 404

        命名慣例 {layer_name}_store 是 Convention（非強制），
        將 store_name 傳入即可覆寫預設化行為。

        【備份行為】
          解壓後的 Shapefile 組件備份至：
            shared_dir/{workspace}/{store_name}/{layer_name}/
          ⚠️ 此備份不影響 GeoServer 服務狀態。

        ZIP 必須包含完整 Shapefile 組件：.shp、.shx、.dbf、.prj

        GeoServer REST：
          PUT /rest/workspaces/{ws}/datastores/{ds}/file.shp
          Content-Type: application/zip, Params: charset=UTF-8, update=overwrite

        Args:
            workspace:   目標工作區名稱
            layer_name:  發布的 Layer 名稱
            file:        Shapefile ZIP 上傳檔
            store_name:  Store 名稱。為 None 時自動產生 {layer_name}_store
            reuse_store: True 表示重用已存在的 Store，
                         False 將建立新 Store（若已存在則 GeoServer 遞覆）

        Returns:
            dict: workspace / store / layer / data_type / reuse_store / service_urls
        """
        if not file.filename.lower().endswith(".zip"):
            raise GeoserverException(400, "僅支援 .zip 格式的 Shapefile 壓縮包")

        # 解析 store_name：未指定時產生預設命名
        resolved_store = store_name if store_name else f"{layer_name}_store"
        content = await file.read()

        # 驗證 ZIP 並重新打包（以 layer_name 統一命名檔案）
        required_exts = {".shp", ".shx", ".dbf", ".prj"}
        found_exts: set = set()

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    ext = Path(name).suffix.lower()
                    if ext in required_exts:
                        found_exts.add(ext)
        except zipfile.BadZipFile:
            raise GeoserverException(400, "無效的 ZIP 檔案格式")

        # 驗證必要組件是否齊全
        missing = required_exts - found_exts
        if missing:
            raise GeoserverException(
                400, f"ZIP 缺少必要的 Shapefile 組件: {sorted(missing)}"
            )

        # 重新打包 ZIP：以 layer_name 命名所有檔案（GeoServer 用此名稱發布圖層）
        repackaged_zip = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(content)) as zf_in:
            with zipfile.ZipFile(repackaged_zip, "w", zipfile.ZIP_DEFLATED) as zf_out:
                for name in zf_in.namelist():
                    ext = Path(name).suffix.lower()
                    if ext in required_exts:
                        zf_out.writestr(f"{layer_name}{ext}", zf_in.read(name))
        repackaged_data = repackaged_zip.getvalue()

        # 備份至共享目錄（供外部存取或除錯用）
        target_dir = Path(self.shared_dir) / workspace / resolved_store / layer_name
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(repackaged_data)) as zf:
            for name in zf.namelist():
                (target_dir / name).write_bytes(zf.read(name))

        # 直接上傳 ZIP 至 GeoServer（不依賴 file:// URI，避免 sandbox 限制）
        url = f"{self.service_url}/rest/workspaces/{workspace}/datastores/{resolved_store}/file.shp"
        headers = {"Content-type": "application/zip"}
        params = {"charset": "UTF-8", "update": "overwrite"}
        r = requests.put(
            url,
            auth=(self.username, self.password),
            data=repackaged_data,
            headers=headers,
            params=params,
        )
        if r.status_code not in (200, 201):
            raise GeoserverException(r.status_code, r.text)

        return {
            "workspace": workspace,
            "store": resolved_store,
            "layer": layer_name,
            "data_type": "vector",
            "reuse_store": reuse_store,
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
        self,
        workspace: str,
        layer_name: str,
        file: UploadFile,
        store_name: Optional[str] = None,
        reuse_store: bool = False,
    ) -> dict:
        """
        上傳 GeoTIFF 並以 CoverageStore 發布 Raster Layer。

        支援兩種策略：

          Dataset 策略（預設，reuse_store=False）：
            upload_layer_tiff(ws, "dem_2024", file)
            → 建立新 CoverageStore「dem_2024_store」，發布 Layer「dem_2024」

          Multi-Layer 策略（reuse_store=True）：
            upload_layer_tiff(ws, "band_ndvi", file,
                              store_name="satellite_store", reuse_store=True)
            → 重用已存在的 CoverageStore「satellite_store」
            ⚠️ CoverageStore 的 Multi-Layer 發布需 GeoServer 對該格式的原生支援

        命名慣例 {layer_name}_store 是 Convention（非強制）。

        【備份行為】
          GeoTIFF 原始檔備份至：
            shared_dir/{workspace}/{store_name}/{layer_name}/{layer_name}.tif
          ⚠️ 此備份不影響 GeoServer 的服務狀態。

        支援副檔名：.tif、.tiff，不嘗試轉檔，不依賴 PostGIS。

        GeoServer REST：
          PUT /rest/workspaces/{ws}/coveragestores/{cs}/file.geotiff
          Content-Type: image/tiff
          Params: configure=all, update=overwrite, coverageName={layer_name}

        Args:
            workspace:   目標工作區名稱
            layer_name:  發布的 Layer 名稱
            file:        GeoTIFF 上傳檔
            store_name:  Store 名稱。為 None 時自動產生 {layer_name}_store
            reuse_store: True 表示重用已存在的 Store

        Returns:
            dict: workspace / store / layer / data_type / reuse_store / service_urls
        """
        filename_lower = file.filename.lower()
        if not (filename_lower.endswith(".tif") or filename_lower.endswith(".tiff")):
            raise GeoserverException(400, "僅支援 .tif 或 .tiff 格式")

        # 解析 store_name：未指定時產生預設命名
        resolved_store = store_name if store_name else f"{layer_name}_store"
        ext = Path(file.filename).suffix.lower()

        # 讀取 GeoTIFF 內容
        content = await file.read()

        # 備份至共享目錄（供外部存取或除錯用）
        target_dir = Path(self.shared_dir) / workspace / resolved_store / layer_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{layer_name}{ext}"
        target_file.write_bytes(content)

        # 直接上傳 GeoTIFF 至 GeoServer（不依賴 file:// URI，避免 sandbox 限制）
        url = (
            f"{self.service_url}/rest/workspaces/{workspace}"
            f"/coveragestores/{resolved_store}/file.geotiff"
        )
        headers = {"Content-type": "image/tiff"}
        params = {"configure": "all", "update": "overwrite", "coverageName": layer_name}
        r = requests.put(
            url,
            auth=(self.username, self.password),
            data=content,
            headers=headers,
            params=params,
        )
        if r.status_code not in (200, 201):
            raise GeoserverException(r.status_code, r.text)

        return {
            "workspace": workspace,
            "store": resolved_store,
            "layer": layer_name,
            "data_type": "raster",
            "reuse_store": reuse_store,
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

    def delete_layer(
        self, workspace: str, layer_name: str, store_name: Optional[str] = None
    ) -> str:
        """
        僅刪除指定 Layer（保留 Store）並清除本地備份。

        適用於 Multi-Layer Store 情境：刪除其中一個 Layer，不影響同一 Store
        下的其他 Layer。若 Store 下僅此一個 Layer，建議改用 delete_dataset()。

        【GeoServer 行為】
          只刪除 Layer 資源，Store 保留。
          REST: DELETE /rest/workspaces/{ws}/layers/{layer}（不加 recurse）

        【備份目錄清理】
          若傳入 store_name，同步清除 shared_dir/{ws}/{store}/{layer}/。
          ⚠️ 此操作僅清除備份副本，不影響 GeoServer 服務。
        """
        url = f"{self.service_url}/rest/workspaces/{workspace}/layers/{layer_name}"
        r = requests.delete(url, auth=(self.username, self.password))
        if r.status_code == 200:
            if store_name:
                try:
                    self.clear_layer_directory(workspace, store_name, layer_name)
                except Exception as e:
                    return f"圖層 {layer_name} 刪除成功，但清除目錄有警告: {e}"
            return f"圖層 {layer_name} 刪除成功（Store 保留）"
        raise GeoserverException(r.status_code, r.content)

    def delete_store(
        self, workspace: str, store_name: str, store_type: str = "datastore"
    ) -> str:
        """
        僅刪除指定 Store（自動遞迴刪除其下所有 Layer）。

        適用於：
          - 已預先刪除全部 Layer，需要清理空的 Store
          - 需要強制刪除含有多個 Layer 的 Store

        【GeoServer 行為】
          recurse=true 會同時刪除 Store 下所有 Layer 與關聯 Resource。

        Args:
            workspace:  工作區名稱
            store_name: Store 名稱
            store_type: "datastore"（向量）或 "coveragestore"（柵格）。預設 datastore。

        REST:
          DELETE /rest/workspaces/{ws}/datastores/{store}?recurse=true
          DELETE /rest/workspaces/{ws}/coveragestores/{store}?recurse=true
        """
        if store_type == "coveragestore":
            url = f"{self.service_url}/rest/workspaces/{workspace}/coveragestores/{store_name}"
        else:
            url = f"{self.service_url}/rest/workspaces/{workspace}/datastores/{store_name}"
        params = {"recurse": "true"}
        r = requests.delete(url, auth=(self.username, self.password), params=params)
        if r.status_code == 200:
            return f"Store {store_name} 刪除成功"
        raise GeoserverException(r.status_code, r.content)

    def delete_dataset(self, workspace: str, store_name: str, layer_name: str) -> str:
        """
        同時刪除 Layer 與其專屬 Store（Dataset 策略的一起刪除）。

        專用於 1:1 Dataset 策略場景：資料集與其接入點同步消失。
        若 Store 下尚有其他 Layer，請改用 delete_layer() 避免誤刪。

        【GeoServer 行為】
          先刪除 Layer 資源，再遞迴刪除 Store，最後清除備份目錄。
          自動偵測 Store 類型（datastore / coveragestore）。

        【備份目錄清理】
          同步刪除 shared_dir/{workspace}/{store_name}/{layer_name}/。
          ⚠️ 此操作僅清除備份副本。
        """
        errors = []

        # 1. 刪除 Layer
        layer_url = (
            f"{self.service_url}/rest/workspaces/{workspace}/layers/{layer_name}"
        )
        r = requests.delete(layer_url, auth=(self.username, self.password))
        if r.status_code not in (200, 404):
            raise GeoserverException(r.status_code, r.content)

        # 2. 嘗試刪除 Store（先嘗試向量 Store，再嘗試柵格 Store）
        for st in ("datastore", "coveragestore"):
            try:
                self.delete_store(workspace, store_name, store_type=st)
                break
            except GeoserverException as e:
                if e.status_code != 404:
                    errors.append(f"Store 刪除失敗({st}): {e.message}")

        # 3. 清除備份目錄
        try:
            self.clear_layer_directory(workspace, store_name, layer_name)
        except Exception as e:
            errors.append(f"備份目錄清除失敗: {e}")

        if errors:
            return f"資料集 {layer_name} 已刪除，但有警告: {'; '.join(errors)}"
        return f"資料集 {layer_name} 刪除成功（Layer + Store 已一併清除）"

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
        # SLD v1.0 使用 application/vnd.ogc.sld+xml
        # SLD v1.1 使用 application/vnd.ogc.se+xml
        headers = {"content-type": "application/vnd.ogc.sld+xml; charset=utf-8"}
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

    def clear_layer_directory(
        self, workspace: str, store_name: str, layer_name: str
    ) -> str:
        """
        清除本地備份目錄中的圖層資料夾（idempotent）。

        刪除 shared_dir/{workspace}/{store_name}/{layer_name}/ 整個目錄。

        【用途定位】
          此方法操作的是「備援稽核目錄」，而非 GeoServer 的 dataDir。
          呼叫此方法不會影響 GeoServer 正在提供服務的 Layer 或 Store。
          通常由 delete_layer() 自動呼叫，或在管理端點中手動觸發。

        【冪等性】
          目錄不存在時不報錯，直接回傳提示訊息。
        """
        import shutil

        target_dir = Path(self.shared_dir) / workspace / store_name / layer_name
        if target_dir.exists():
            shutil.rmtree(target_dir)
            return f"已刪除圖層目錄: {target_dir}"
        return f"圖層目錄不存在，無需清理: {target_dir}"
