#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${1:-./logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/upgrade_$(date +'%Y%m%d_%H%M%S').txt"

{
  echo "===== 診斷開始：$(date '+%F %T') ====="

  # [1] 更新套件索引
  echo -e "\n[1/7] 更新套件索引"
  sudo apt update

  # [2] 升級模擬（不變更系統）
  echo -e "\n[2/7] 升級模擬（不會改動系統）"
  sudo apt-get -s upgrade || true

  # [3] 實際升級
  echo -e "\n[3/7] 實際升級"
  sudo apt upgrade -y

  # [4] Full-upgrade（處理相依性變更）
  echo -e "\n[4/7] Full-upgrade（必要相依性變更）"
  sudo apt full-upgrade -y

  # [5] 清理
  echo -e "\n[5/7] 自動清除不再需要的套件"
  sudo apt autoremove --purge -y

  # [6] 升級後快照
  echo -e "\n[6/7] 升級後仍可更新的套件（應為空）"
  apt list --upgradable || true

  # [7] 健檢與是否需要重開機
  echo -e "\n[7/7] 額外診斷資訊"
  echo "[A] 磁碟使用量"; df -h /
  echo "[B] 需要重開機？"; if [ -f /var/run/reboot-required ]; then echo "建議"; else echo "不需要"; fi

  echo "===== 全流程結束：$(date '+%F %T') ====="
} | tee -a "$LOG_FILE" 2>&1

echo "📄 升級記錄已寫入：$LOG_FILE"
