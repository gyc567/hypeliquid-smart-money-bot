# 🤖 Hypeliquid聪明钱地址监控机器人

一个Telegram机器人，用于监控Hypeliquid链上的聪明钱地址动态，实时推送余额变化和交易活动通知。

## 🌟 功能特性

- **🔍 智能监控**: 实时监控Hypeliquid链上地址的动态
- **💰 余额变化**: 检测地址余额的增减变化
- **🔄 交易检测**: 自动识别新的链上交易活动
- **📱 Telegram推送**: 通过Telegram实时推送通知
- **⚡ 高性能**: 支持多地址并行监控，可扩展架构
- **🔧 可配置**: 灵活的扫描间隔和监控参数设置
- **🛡️ 稳定可靠**: 完善的错误处理和重试机制

## 🚀 快速开始

### 1. 获取Telegram Bot Token

1. 在Telegram中搜索 [@BotFather](https://t.me/botfather)
2. 发送 `/newbot` 命令创建新机器人
3. 按照提示设置机器人名称和用户名
4. 保存获得的Bot Token

### 2. 部署方式选择

#### 方式一：Docker部署（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-repo/hypeliquid-smart-money-bot.git
cd hypeliquid-smart-money-bot

# 复制环境配置文件
cp .env.example .env

# 编辑配置文件，设置TELEGRAM_BOT_TOKEN
nano .env

# 使用部署脚本一键部署
chmod +x scripts/deploy.sh
./scripts/deploy.sh --docker deploy
```

#### 方式二：本地部署

```bash
# 克隆仓库
git clone https://github.com/your-repo/hypeliquid-smart-money-bot.git
cd hypeliquid-smart-money-bot

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 复制并配置环境变量
cp .env.example .env
# 编辑.env文件，设置TELEGRAM_BOT_TOKEN

# 运行机器人
python main.py
```

### 3. 使用机器人

在Telegram中找到你的机器人，发送以下命令：

- `/start` - 开始使用机器人
- `/help` - 查看帮助信息
- `/add 0x地址 [标签]` - 添加监控地址
- `/remove 0x地址` - 移除监控地址
- `/list` - 查看监控列表
- `/setinterval 秒数` - 设置扫描间隔
- `/status` - 查看机器人状态

## 📋 命令详解

### 添加监控地址
```
/add 0xb317d2bc2d3d2df5fa441b5bae0ab9d8b07283ae 聪明钱1
```

### 设置扫描间隔
```
/setinterval 120  # 设置为2分钟扫描一次
```

### 查看监控列表
```
/list
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token（必需） | - |
| `HYPERLIQUID_RPC_URL` | Hyperliquid RPC节点 | `https://rpc.hyperliquid.xyz/evm` |
| `DATABASE_PATH` | 数据库文件路径 | `./data/smart_money_monitor.db` |
| `DEFAULT_SCAN_INTERVAL` | 默认扫描间隔（秒） | `60` |
| `MAX_ADDRESSES_PER_USER` | 每个用户最大监控地址数 | `20` |
| `API_RATE_LIMIT` | API请求速率限制（请求/秒） | `2` |
| `REQUEST_TIMEOUT` | 请求超时时间（秒） | `10` |
| `LOG_LEVEL` | 日志级别 | `INFO` |

### 监控配置

- **扫描间隔**: 建议设置为60-300秒，平衡实时性和资源消耗
- **地址限制**: 每个用户最多监控20个地址，防止滥用
- **速率限制**: API请求限制为每秒2次，避免被封禁

## 🏗️ 架构设计

### 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram      │    │   监控机器人     │    │  Hyperliquid    │
│   用户界面       │◄──►│   核心逻辑       │◄──►│   区块链数据     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   数据库        │
                       │   SQLite        │
                       └─────────────────┘
```

### 核心模块

- **Telegram Bot**: 用户交互和命令处理
- **数据获取器**: 从Hyperliquid获取链上数据
- **地址监控器**: 检测地址变化和交易活动
- **消息格式化器**: 格式化推送消息内容
- **任务调度器**: 管理定时任务和后台服务
- **错误处理器**: 统一的错误处理和重试机制

## 🔧 部署管理

### Docker管理命令

```bash
# 查看服务状态
./scripts/deploy.sh --docker status

# 查看日志
./scripts/deploy.sh --docker logs

# 停止服务
./scripts/deploy.sh --docker stop

# 重启服务
./scripts/deploy.sh --docker restart

# 更新代码
./scripts/deploy.sh --docker update

# 清理数据
./scripts/deploy.sh --docker cleanup
```

### 本地管理命令

```bash
# 如果使用systemd服务
sudo systemctl start hypeliquid-bot
sudo systemctl stop hypeliquid-bot
sudo systemctl status hypeliquid-bot
sudo systemctl restart hypeliquid-bot

# 查看日志
sudo journalctl -u hypeliquid-bot -f
tail -f logs/bot.log
```

## 📊 监控和统计

### 系统统计

机器人每小时会生成统计报告，包括：

- 监控地址数量
- 检测到的变化数量
- 发送的通知数量
- 系统运行时间
- 错误处理统计

### 性能指标

- **响应时间**: 平均<1秒
- **扫描频率**: 可配置，默认60秒
- **并发处理**: 支持多用户多地址并行监控
- **内存使用**: 约100-200MB
- **CPU使用**: 正常<5%，扫描时<20%

## 🛡️ 安全和稳定性

### 错误处理

- **重试机制**: 网络请求自动重试，指数退避
- **熔断器**: 防止故障蔓延，保护系统稳定性
- **异常捕获**: 所有关键操作都有异常处理
- **日志记录**: 详细的错误日志和追踪信息

### 安全措施

- **输入验证**: 严格验证用户输入的地址格式
- **速率限制**: API请求和用户消息都有速率限制
- **资源限制**: Docker容器有CPU和内存限制
- **数据隔离**: 用户数据相互隔离，保护隐私

## 🐛 故障排查

### 常见问题

1. **机器人无法启动**
   - 检查 `TELEGRAM_BOT_TOKEN` 是否正确设置
   - 查看日志文件 `logs/bot.log`
   - 确保网络连接正常

2. **地址监控失败**
   - 检查地址格式是否正确
   - 确认Hyperliquid RPC节点可用
   - 查看API速率限制是否触发

3. **通知无法发送**
   - 检查Telegram Bot是否被用户屏蔽
   - 确认机器人有发送消息的权限
   - 查看错误日志获取详细信息

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python main.py
```

### 健康检查

```bash
# Docker健康检查
docker-compose exec hypeliquid-bot python -c "from main import check_health; import asyncio; asyncio.run(check_health())"
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/your-repo/hypeliquid-smart-money-bot.git
cd hypeliquid-smart-money-bot

# 创建开发环境
python3 -m venv venv
source venv/bin/activate

# 安装开发依赖
pip install -r requirements.txt
pip install pytest black flake8

# 运行测试
pytest tests/

# 代码格式化
black .
flake8 .
```

### 提交规范

- 使用清晰的提交信息
- 添加适当的测试用例
- 更新相关文档
- 遵循PEP 8代码规范

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API库
- [Web3.py](https://github.com/ethereum/web3.py) - 以太坊交互库
- [Hyperliquid](https://hyperliquid.xyz/) - 提供区块链数据

## 📞 支持

如果你遇到任何问题或有功能建议，请通过以下方式联系：

- 提交GitHub Issue
- 发送邮件到: your-email@example.com
- Telegram: @your_username

---

**免责声明**: 本工具仅供学习和研究使用，不构成投资建议。加密货币投资存在风险，请谨慎决策。监控聪明钱地址并不能保证投资成功，请根据自己的判断做出投资决策。 

**风险提示**: 使用本机器人即表示您理解并承担所有相关风险。开发者不对任何投资损失负责。