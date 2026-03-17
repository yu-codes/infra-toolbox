#!/bin/bash

INPUT="hosts.txt"

echo "測試結果："
echo "Host:Port => 狀態"

while read host port; do
    # 去掉註解或空行
    [[ "$host" =~ ^#.*$ ]] && continue
    [[ -z "$host" ]] && continue

    # 測 TCP 連線
    nc -vz -w 5 "$host" "$port" &>/tmp/nc_result.txt
    if grep -q "succeeded" /tmp/nc_result.txt; then
        echo "$host:$port => 可連"
    else
        echo "$host:$port => 無法連"
    fi
done < "$INPUT"
