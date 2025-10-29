#!/bin/bash

# 日志轮转脚本

LOG_DIR="/logs"
MAX_SIZE="100M"
MAX_AGE=7  # 天数
MAX_FILES=10

# 检查日志目录
if [ ! -d "$LOG_DIR" ]; then
    echo "日志目录不存在: $LOG_DIR"
    exit 1
fi

# 轮转日志文件
for log_file in "$LOG_DIR"/*.log; do
    if [ -f "$log_file" ]; then
        # 检查文件大小
        file_size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo 0)
        max_size_bytes=$(numfmt --from=iec "$MAX_SIZE" 2>/dev/null || echo 104857600)  # 默认100MB
        
        if [ "$file_size" -gt "$max_size_bytes" ]; then
            echo "轮转日志文件: $log_file"
            
            # 创建带时间戳的备份
            timestamp=$(date +%Y%m%d_%H%M%S)
            backup_file="${log_file}.${timestamp}"
            
            # 移动当前日志
            mv "$log_file" "$backup_file"
            
            # 创建新的空日志文件
            touch "$log_file"
            
            # 压缩备份文件
            gzip "$backup_file"
        fi
    fi
done

# 清理旧日志文件
find "$LOG_DIR" -name "*.log.*" -type f -mtime +$MAX_AGE -delete 2>/dev/null || true

# 限制备份文件数量
for log_file in "$LOG_DIR"/*.log; do
    if [ -f "$log_file" ]; then
        base_name=$(basename "$log_file" .log)
        backup_count=$(find "$LOG_DIR" -name "${base_name}.log.*" -type f | wc -l)
        
        if [ "$backup_count" -gt "$MAX_FILES" ]; then
            # 删除最旧的备份文件
            find "$LOG_DIR" -name "${base_name}.log.*" -type f -printf '%T@ %p\n' | \
                sort -n | head -n -$MAX_FILES | cut -d' ' -f2- | xargs rm -f
        fi
    fi
done

echo "日志轮转完成: $(date)"