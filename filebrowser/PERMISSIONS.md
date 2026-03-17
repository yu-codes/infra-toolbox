# FileBrowser 檔案權限設置指南

## 問題描述

透過 FileBrowser 上傳的檔案，其他服務 (如 nginx、應用程序等) 無法存取。這是因為容器內上傳檔案的所有權和權限設置不當。

本指南涵蓋：
- 查詢系統用戶和群組信息
- 配置 FileBrowser 容器的運行用戶
- 設置檔案系統權限
- 多服務之間的權限協調

## 前置準備：查詢用戶和群組 ID

在配置前，先查詢各個服務使用者的 ID 和群組信息。

### 查詢用戶 ID 和群組 ID

```bash
# 查詢特定用戶的 uid 和群組信息
id <用戶名>

# 例如：
id nginx          # 查詢 nginx 用戶
id www-data       # 查詢 www-data 用戶
id $(whoami)      # 查詢目前用戶

# 輸出範例：
# uid=1000(app_user) gid=1000(app_user) groups=1000(app_user),4(adm),24(cdrom)
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### 查詢用戶所在的群組

```bash
# 查詢用戶所在的所有群組
groups <用戶名>

# 例如：
groups nginx      # 查詢 nginx 所在的群組
groups www-data   # 查詢 www-data 所在的群組

# 輸出範例：
# nginx : nginx app_user
# www-data : www-data
```

### 查詢檔案和目錄的所有者和群組

```bash
# 查詢檔案或目錄的所有者和群組
ls -ld /path/to/directory

# 查詢目錄下所有檔案的權限
ls -la /path/to/directory

# 輸出說明：
# drwxrwsr-x 3 app_user app_user 4096 Mar 13 09:02 /data/uploads
# |          |  |        |        |                 |
# |          |  |        |        時間戳             目錄路徑
# |          |  |        群組名
# |          |  所有者名
# |          硬連結數
# 權限和特殊位 (s = setgid)
```

### 理解權限輸出

一個典型的權限輸出看起來像這樣：

```
-rw-rw-r-- 1 app_user app_user 104692 Mar 13 09:24 document.pdf
|          | |        |        |      |           |
|          | |        |        |      |           檔案名稱
|          | |        |        檔案大小
|          | |        修改時間
|          | 群組（app_user）
|          所有者（app_user）
|
權限：-rw-rw-r--
  |   ||  |  |
  |   ||  |  其他人的權限：r-- (只讀)
  |   ||  群組的權限：rw- (讀寫)
  |   |所有者的權限：rw- (讀寫)
  |   檔案類型：- 表示普通文件，d 表示目錄
```

## 解決方案

### 1. 確定目標用戶 ID

首先確定 FileBrowser 容器應該以哪個用戶身份運行。通常有兩種方案：

**方案 A：使用主機用戶 (推薦)**
```bash
# 查詢要使用的用戶名 (例如需要存取 nginx 檔案)
id nginx        # 記下 uid 和 gid
# uid=33(www-data) gid=33(www-data)

# 或查詢應用程序用戶
id app_user     # 記下 uid 和 gid
# uid=1000(app_user) gid=1000(app_user)
```

**方案 B：使用現有用戶**
- 容器內預設用戶（不適合多服務權限共享）

### 2. 修改 docker-compose.yml

根據查詢結果修改 `docker-compose.yml`，設置容器運行用戶：

```yaml
services:
  filebrowser:
    image: filebrowser/filebrowser:latest
    container_name: filebrowser
    user: "1000:1000"              # 改為查詢結果的 uid:gid
    # 例如：
    # user: "33:33"                # 對應 www-data 用戶
    # user: "1000:1000"            # 對應 app_user 用戶
    ports:
      - "10020:80"
    volumes:
      - ./data:/srv
      - ./database:/database
    networks:
      - infra-toolbox-network
    restart: unless-stopped
```

**說明：**
- `user: "uid:gid"` - 容器以該用戶身份運行，上傳檔案將以此用戶為所有者
- 確保 uid:gid 與主機系統一致

### 3. 配置檔案系統權限

在啟動容器前，設置上傳目錄的權限：

```bash
# 進入 filebrowser 目錄
cd /path/to/filebrowser

# 1. 設置目錄的 setgid 位
#    新檔案將自動繼承目錄的群組
sudo chmod g+s ./data

# 2. 設置群組可讀寫
sudo chmod g+rw ./data

# 3. 設置所有子目錄權限
sudo chmod -R g+rw ./data

# 4. 驗證權限設置
ls -ld ./data
# 應該看到類似：drwxrwsr-x
```

### 4. 多服務權限協調 (可選)

若需讓多個服務存取 FileBrowser 上傳的檔案：

```bash
# 1. 建立共享群組 (僅主機環境)
sudo groupadd fileshare         # 如果群組不存在

# 2. 添加要共享檔案的服務用戶到群組
sudo usermod -a -G fileshare www-data     # nginx/web 服務
sudo usermod -a -G fileshare app_user     # 應用程序用戶

# 3. 修改 Docker Compose 容器用戶
# user: "<uid>:<gid>"             # 其中 <gid> 是 fileshare 的群組 ID

# 4. 驗證群組設置
groups www-data
# 應該看到：www-data : www-data fileshare
```

### 5. 啟動或重啟容器

```bash
# 停止現有容器（若有）
docker compose down

# 啟動容器
docker compose up -d

# 檢查容器狀態
docker compose ps
docker compose logs -f
```

## 權限驗證

上傳檔案後，驗證權限是否正確：

```bash
# 檢查上傳目錄的權限
ls -ld ./data

# 應該看到類似的輸出：
# drwxrwsr-x  3 app_user app_user  4096 Mar 13 09:17 ./data
#
# 檢查包含 s 位（setgid）

# 檢查上傳的檔案權限
ls -la ./data/

# 應該看到：
# -rw-rw-r-- 1 app_user app_user  104692 Mar 13 09:17 uploaded_file.pdf
#
# 檢查點：
# - 權限：-rw-rw-r-- (664)
# - 所有者：app_user (與 docker-compose.yml 的 user 一致)
# - 群組：app_user
```

## 權限說明

| 項目 | 所有者 | 群組 | 其他 |
|------|--------|------|------|
| 檔案 (664) | rw- | rw- | r-- |
| 目錄 (775, setgid) | rwx | rwx | r-x |

- **所有者**: 檔案建立者，擁有完全控制
- **群組**: 群組成員可讀寫（用以共享存取）
- **其他**: 其他用戶僅讀或無權限

## 故障排除

### 問題：上傳的檔案所有者是 `root` 或其他用戶

**原因：** docker-compose.yml 中的 `user` 設置不正確

**解決方案：**
1. 複查正確的 uid:gid：`id www-data` 或 `id app_user`
2. 修改 docker-compose.yml 中的 `user` 設定為正確值
3. 重啟容器：`docker compose down && docker compose up -d`

### 問題：其他服務無法讀寫 FileBrowser 上傳的檔案

**原因：** 群組權限未正確設置

**解決方案：**
1. 驗證群組設置：
   ```bash
   groups www-data       # 檢查服務用戶的群組
   ls -la ./data/        # 檢查檔案的群組權限
   ```
2. 若群組不同，執行：
   ```bash
   sudo chmod -R g+rw ./data    # 確保群組可讀寫
   ```
3. 重啟相依的服務

### 問題：無法找到合適的 uid:gid

**解決方案：**
```bash
# 查詢所有本地用戶和其 uid
getent passwd

# 查詢所有本地群組和其 gid
getent group

# 篩選特定服務
getent passwd | grep nginx
getent group | grep www-data
```

### 問題：setgid 位未生效

**原因：** 檔案系統不支援或權限設置有誤

**驗證方案：**
```bash
# 檢查 setgid 位
stat ./data | grep Access
# 應該看到 (0755, Uid: ..., Gid: ...) 包含 s 位

# 重新設置
sudo chmod g+s ./data
sudo chmod -R g+rw ./data

# 驗證
ls -ld ./data
# 應該看到 drwxrwsr-x 中的 s
```

## 參考資訊

- **FileBrowser 官方映像**: [filebrowser/filebrowser](https://hub.docker.com/r/filebrowser/filebrowser)
- **Linux 權限模式**:
  - 664 (rw-rw-r--): 所有者和群組讀寫，其他唯讀
  - 775 (rwxrwxr-x): 所有者和群組完全控制，其他唯讀執行
  - setgid 位: 新檔案與目錄自動繼承父目錄的群組
