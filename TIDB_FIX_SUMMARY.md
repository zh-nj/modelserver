# TiDB 数据库问题修复总结

## 问题描述

在部署 LLM 推理服务时遇到了 TiDB 数据库相关的问题，主要包括：

1. **外键约束不兼容问题**：TiDB 对外键约束的处理与标准 MySQL 有所不同
2. **临时空间不足问题**：TiDB 在创建索引时需要大量临时空间，但 `/tmp` 目录空间不足
3. **应用代码问题**：部分服务类缺少必要的方法

## 解决方案

### 1. TiDB 数据目录迁移

将 TiDB 数据目录从默认的 `/tmp` 迁移到 `/mnt/DATA/datas/tidb`：

```bash
# 创建数据目录
mkdir -p /mnt/DATA/datas/tidb

# 使用新的数据目录启动 TiDB
cd /mnt/DATA/datas/tidb
TMPDIR=/mnt/DATA/datas/tidb/tmp tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379 --tag llm-inference
```

### 2. 数据库模型优化

移除了所有数据库表的索引定义以避免 TiDB 临时空间问题：

```python
# 原来的索引定义（已注释）
# __table_args__ = (
#     Index('idx_model_priority', 'priority'),
#     Index('idx_model_framework', 'framework'),
#     Index('idx_model_active', 'is_active'),
#     Index('idx_model_created', 'created_at'),
# )
```

### 3. 外键约束移除

移除了所有外键约束以提高 TiDB 兼容性：

```python
# 原来的外键定义
# model_id = Column(String(255), ForeignKey('model_configs.id'), nullable=False)

# 修改后的定义
model_id = Column(String(255), nullable=False, comment="模型ID")
```

### 4. 应用代码修复

修复了服务初始化过程中的方法调用问题：

- `ModelHealthChecker.initialize()` → `ModelHealthChecker.start()`
- 移除了 `APIProxyService.start()` 调用，因为该服务是无状态的

### 5. 数据库连接配置

更新了数据库连接配置以使用正确的 TiDB IP 地址：

```bash
# 更新 .env 文件
DATABASE_URL=mysql+pymysql://root:@192.168.4.109:4000/llm_inference?charset=utf8mb4
```

## 部署结果

✅ **部署成功**！服务现在正常运行：

- **后端服务**：http://localhost:8000
- **API 文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/health

## 数据库状态

成功创建的数据库表：

```sql
mysql> SHOW TABLES;
+-------------------------+
| Tables_in_llm_inference |
+-------------------------+
| alert_events            |
| alert_history           |
| alert_rules             |
| alert_rules_v2          |
| config_backups          |
| config_change_logs      |
| gpu_metrics             |
| model_configs           |
| model_status            |
| system_configs          |
| system_metrics          |
+-------------------------+
```

## 后续优化建议

1. **索引优化**：在生产环境中，可以考虑逐步添加必要的索引，确保有足够的临时空间
2. **监控配置**：配置 TiDB 的监控和告警
3. **备份策略**：制定数据备份和恢复策略
4. **性能调优**：根据实际使用情况调优 TiDB 配置参数

## 启动命令

```bash
# 启动 TiDB（在数据目录中）
cd /mnt/DATA/datas/tidb
TMPDIR=/mnt/DATA/datas/tidb/tmp tiup playground --db 1 --pd 1 --kv 1 --tiflash 0 --host 0.0.0.0 --db.port 4000 --pd.port 2379 --tag llm-inference &

# 部署服务
./scripts/deploy-source.sh development --no-frontend
```

## 总结

通过以上修复，成功解决了 TiDB 数据库的兼容性问题，服务现在可以正常启动和运行。主要的解决思路是：

1. 避免使用 TiDB 不完全支持的特性（外键约束）
2. 解决临时空间不足的问题（迁移数据目录）
3. 修复应用代码中的方法调用错误

这为后续的开发和部署提供了稳定的基础。