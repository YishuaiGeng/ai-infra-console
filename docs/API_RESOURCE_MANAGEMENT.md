# API 资源管理模块开发文档

## 1. 文档状态

- 状态：Implemented / 核心功能已完成
- 创建日期：2026-08-10
- 实现日期：2026-08-10
- 适用项目：AI Infra Console
- 建议阶段：Phase 10
- 模块名称：API Resources / API 资源
- 目标用户：个人研究者、AI 开发者、小型实验室管理员

本文档定义 AI Infra Console 的 API 资产管理扩展。该模块用于统一记录和管理本地推理 API 与外部模型平台 API，重点解决“有哪些 API、属于谁、可以调用哪些模型、当前是否可用、额度和使用量如何”的问题。

该模块不是 API 网关，不接管正常业务请求，不进行请求转发、协议转换、负载均衡或二级 Key 分发。

当前实现覆盖 Provider Registry、Account、AES-256-GCM Credential 加密、Credential 验证与轮换、模型同步、人工模型/余额/用量快照、OpenAI 组织级 Usage/Costs 同步、同步历史、审计、Admin/Viewer 权限、SSRF 策略、BFF 和控制台页面。Generic OpenAI-compatible Provider 仅声明 Credential 验证与模型发现能力，不虚构余额或用量接口。

## 2. 背景

当前 AI Infra Console 已经能够管理服务器、GPU、模型文件和 vLLM Deployment，并在 `/apis` 页面展示由本系统创建的 OpenAI-compatible Endpoint。

现有 Endpoint 的生命周期与 `Deployment` 强绑定，适合回答以下问题：

- 哪个本地模型已经部署？
- 部署在哪台服务器和哪个端口？
- Endpoint 是否健康？
- 能否通过 `/v1/chat/completions` 完成一次测试？

但它不能回答外部 API 资产管理问题：

- 当前拥有哪些模型平台账号？
- 每个平台配置了哪些 API Key？
- 哪些项目或人员在使用这些资源？
- 每个账号能够调用哪些模型？
- Key 是否有效、何时到期、是否需要轮换？
- 平台余额、额度、本月费用和 Token 使用量是多少？
- 哪些平台长时间未使用或出现异常？

因此需要在现有 Deployment Endpoint 之外增加独立的 API Resource 领域模型。

## 3. 产品定位

API 资源管理模块是一个 API 资产台账、健康检测与用量同步控制台。

核心定位：

```text
API Resources
  ├── Local Inference APIs
  │     └── 来自 AI Infra Console Deployment
  └── External API Accounts
        ├── Provider / 平台
        ├── Account / 账号或项目
        ├── Credential / 凭据
        ├── Models / 可用模型
        ├── Health / 连通性
        └── Usage / 余额与用量快照
```

系统提供统一展示和管理，但外部应用仍然直接调用原平台 API。

## 4. 目标与非目标

### 4.1 目标

1. 建立本地推理 API 与外部 API 的统一资产目录。
2. 支持多个供应商、多个账号和多个 Credential。
3. 安全保存 API Credential，并在界面中只显示掩码。
4. 检测 Base URL、Credential 和模型访问能力。
5. 同步供应商支持的模型、余额、额度和使用量。
6. 支持人工维护供应商不提供的额度和账单信息。
7. 提供按平台、账号、模型、项目和时间范围的统计视图。
8. 提供过期、失效、额度不足和同步失败通知。
9. 所有敏感操作进入审计日志。
10. 保持 AI Infra Console 的无通用代理、无任意命令安全边界。

### 4.2 非目标

首个版本明确不实现：

- 通用 API Gateway。
- OpenAI 与 Anthropic 请求格式互转。
- 业务请求代理和转发。
- 模型请求负载均衡或故障转移。
- 二级 API Key 签发。
- 用户级请求限流。
- 请求内容、Prompt 或模型输出记录。
- 代理层 Token 计量。
- 自动充值或自动购买额度。
- 浏览器提交任意 URL 后由 Central 发起任意 HTTP 请求。
- 将外部 API Key 分发给 Agent。

未来若需要网关能力，应作为独立模块设计，不应隐式扩展本模块的健康检测接口。

## 5. 术语

| 术语 | 定义 |
| --- | --- |
| Provider | API 平台或服务提供方，例如 OpenAI、Anthropic、阿里云百炼或自定义 OpenAI-compatible 服务 |
| Account | Provider 下的一个账号、项目、Workspace 或计费主体 |
| Credential | Account 使用的 API Key、Token 或其他认证材料 |
| External API | 不由当前 AI Infra Console Deployment 创建的 API |
| Local Inference API | 由本系统管理的 vLLM 等本地推理 Endpoint |
| Capability | Provider Adapter 支持的能力，例如模型发现、余额同步、用量同步和健康检测 |
| Usage Snapshot | 某个时间区间或时间点的供应商用量数据 |
| Balance Snapshot | 某个时间点的余额或剩余额度数据 |
| Sync Run | 一次模型、余额或用量同步任务及其执行结果 |

## 6. 用户角色与权限

沿用现有 `Admin` 和 `Viewer` 角色。

### 6.1 Admin

- 创建、编辑、归档 Provider Account。
- 创建、轮换、禁用和删除 Credential。
- 执行 Credential 验证和模型发现。
- 手动触发余额和用量同步。
- 配置自动同步策略。
- 查看掩码后的 Credential 信息。
- 查看用量、费用、健康状态和同步错误。
- 导出不包含明文 Credential 的资产与用量报表。

### 6.2 Viewer

- 查看 Provider、Account、模型、健康状态和用量。
- 查看 Credential 名称、掩码、状态和到期时间。
- 不允许创建、修改、验证或删除 Credential。
- 不允许查看或导出明文 Credential。

### 6.3 明文 Credential 规则

- 创建时允许提交明文。
- 后端加密保存后，不再通过 API 返回明文。
- 编辑 Credential 必须提交新的完整值，不能基于掩码修改。
- 页面刷新、审计日志、错误响应和导出文件中不得出现明文。

## 7. 用户故事

### 7.1 资产登记

作为 Admin，我可以登记一个外部 API 账号，包括平台、用途、负责人、Base URL、Credential、标签和备注，以便知道该资源属于谁以及用于什么项目。

### 7.2 Credential 状态

作为 Admin，我可以看到 Credential 是否有效、最后验证时间、到期时间和最后错误，但看不到保存后的完整 Key。

### 7.3 模型发现

作为 Admin，我可以同步账号能够访问的模型列表，并看到模型标识、显示名称、能力和最近发现时间。

### 7.4 用量查看

作为 Admin 或 Viewer，我可以按日、周、月查看供应商公开提供的请求量、Token、费用、额度和余额数据。

### 7.5 手工维护

当 Provider 不提供用量 API 时，作为 Admin，我可以维护人工余额、预算或账单记录，并清楚看到数据来源为 `manual`。

### 7.6 异常提醒

作为 Admin，我可以收到 Credential 失效、同步连续失败、余额不足、预算接近耗尽和 Credential 即将到期的通知。

### 7.7 本地与外部统一查看

作为用户，我可以在 API Resources 总览中同时看到本地 vLLM Endpoint 和外部平台账号，但二者的配置与生命周期保持独立。

## 8. 信息架构

建议将现有导航中的 `API Endpoints` 调整为 `API Resources`，包含以下页面：

```text
/api-resources
  总览：资产数量、健康状态、余额、费用、异常

/api-resources/local
  本地推理 API：现有 Deployment Endpoint 页面迁移到此处

/api-resources/external
  外部 API：Provider Account 列表

/api-resources/external/new
  新建外部 API Account

/api-resources/external/[accountId]
  Account 详情：Credential、Models、Usage、Sync、Audit

/api-resources/usage
  跨平台用量与费用统计

/api-resources/providers
  Provider Adapter 能力和全局状态
```

为了兼容已有书签，`/apis` 可以重定向到 `/api-resources/local`。

## 9. 页面设计

### 9.1 总览页

展示：

- External Account 数量。
- Active Credential 数量。
- Credential 异常数量。
- 本地推理 Endpoint 数量。
- 最近 30 天已同步费用。
- 已知余额和剩余额度。
- 最近同步失败数量。
- 即将到期 Credential。
- Provider 健康分布。
- 数据新鲜度提示。

### 9.2 外部 API 列表

字段：

- Provider 图标和名称。
- Account 名称。
- 用途或所属项目。
- Base URL。
- Credential 状态。
- 可用模型数量。
- 余额或额度摘要。
- 本月费用。
- 最近验证时间。
- 最近同步时间。
- 标签。

支持搜索、Provider 筛选、状态筛选、标签筛选和归档筛选。

### 9.3 Account 详情

分为以下 Tab：

1. `Overview`
   - 基本信息、负责人、标签、备注和状态。
2. `Credentials`
   - Credential 掩码、状态、到期时间、轮换和验证。
3. `Models`
   - 可用模型、能力、上下文长度和发现来源。
4. `Usage`
   - 请求量、Token、费用、额度和余额趋势。
5. `Sync History`
   - 同步类型、状态、耗时、数据区间和安全错误。
6. `Activity`
   - 与该 Account 相关的审计日志。

### 9.4 新建 Account 表单

步骤：

1. 选择 Provider。
2. 填写名称、项目、负责人、Base URL 和标签。
3. 填写 Credential。
4. 执行连接验证。
5. 展示 Adapter 能力。
6. 选择自动同步项目和周期。
7. 保存。

连接验证失败时允许保存为 `unverified`，但必须显示明确警告。

## 10. 领域模型

### 10.1 `api_providers`

Provider 定义由代码内置，数据库保存运行时配置与展示覆盖。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `slug` | String(64), unique | 稳定标识，例如 `openai`、`anthropic`、`aliyun-bailian`、`generic-openai` |
| `display_name` | String(128) | 展示名称 |
| `provider_type` | String(32) | `built_in` 或 `custom` |
| `default_base_url` | String(512), nullable | 默认 Base URL |
| `capabilities` | JSON | Adapter 能力声明 |
| `is_enabled` | Boolean | 是否允许新建 Account |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

### 10.2 `api_accounts`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `provider_id` | UUID, FK | Provider |
| `name` | String(128) | Account 名称 |
| `purpose` | String(255), nullable | 用途或项目 |
| `owner` | String(128), nullable | 负责人 |
| `base_url` | String(512) | 实际 Base URL |
| `status` | String(32) | `active`、`unverified`、`degraded`、`disabled`、`archived` |
| `billing_currency` | String(16), nullable | 费用币种 |
| `monthly_budget` | Numeric, nullable | 人工配置的月预算 |
| `tags` | JSON | 标签数组 |
| `notes` | Text, nullable | 非敏感备注 |
| `last_verified_at` | DateTime, nullable | 最近验证时间 |
| `last_synced_at` | DateTime, nullable | 最近成功同步时间 |
| `created_by_user_id` | UUID, FK | 创建人 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

约束：同一个 Provider 下 Account 名称可以重复，但建议对 `(provider_id, name, base_url)` 建普通索引。

### 10.3 `api_credentials`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `account_id` | UUID, FK | 所属 Account |
| `name` | String(128) | Credential 名称 |
| `credential_type` | String(32) | 首版仅支持 `api_key`、`bearer_token` |
| `encrypted_value` | LargeBinary/Text | 加密密文 |
| `encryption_key_version` | String(32) | 密钥版本 |
| `masked_value` | String(64) | 例如 `sk-****abcd` |
| `fingerprint` | String(64), index | HMAC 指纹，用于检测重复 Credential |
| `status` | String(32) | `active`、`invalid`、`expired`、`disabled` |
| `expires_at` | DateTime, nullable | 到期时间 |
| `last_validated_at` | DateTime, nullable | 最近验证时间 |
| `last_error_code` | String(64), nullable | 安全错误码 |
| `last_error_message` | String(512), nullable | 清洗后的错误信息 |
| `created_by_user_id` | UUID, FK | 创建人 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

Credential 删除建议使用真实删除；Account 删除采用归档，防止历史 Usage 失去归属。

### 10.4 `api_account_models`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `account_id` | UUID, FK | Account |
| `provider_model_id` | String(255) | Provider 返回的模型 ID |
| `display_name` | String(255), nullable | 展示名称 |
| `model_family` | String(128), nullable | 模型家族 |
| `capabilities` | JSON | chat、embedding、image、audio 等 |
| `context_window` | BigInteger, nullable | 上下文长度 |
| `is_available` | Boolean | 最近一次发现是否可用 |
| `source` | String(32) | `provider` 或 `manual` |
| `discovered_at` | DateTime | 首次发现时间 |
| `last_seen_at` | DateTime | 最近发现时间 |

唯一约束：`(account_id, provider_model_id)`。

### 10.5 `api_usage_snapshots`

保存聚合数据，不保存 Prompt、Response 或业务请求内容。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `account_id` | UUID, FK | Account |
| `credential_id` | UUID, FK, nullable | Provider 能区分 Credential 时填写 |
| `provider_model_id` | String(255), nullable | Provider 能区分模型时填写 |
| `period_start` | DateTime | 统计周期开始 |
| `period_end` | DateTime | 统计周期结束 |
| `granularity` | String(16) | `hour`、`day`、`month` |
| `request_count` | BigInteger, nullable | 请求量 |
| `input_tokens` | BigInteger, nullable | 输入 Token |
| `output_tokens` | BigInteger, nullable | 输出 Token |
| `cached_tokens` | BigInteger, nullable | 缓存 Token |
| `total_tokens` | BigInteger, nullable | 总 Token |
| `cost_amount` | Numeric, nullable | 费用 |
| `currency` | String(16), nullable | 币种 |
| `source` | String(32) | `provider_api`、`invoice_import`、`manual` |
| `provider_record_id` | String(255), nullable | 去重标识 |
| `raw_metadata` | JSON | 不含 Credential 和请求内容的扩展数据 |
| `collected_at` | DateTime | 采集时间 |

去重约束根据 Adapter 能力选择：

- 有稳定供应商记录 ID：`(account_id, provider_record_id)`。
- 无稳定 ID：`(account_id, credential_id, provider_model_id, period_start, period_end, source)`。

### 10.6 `api_balance_snapshots`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `account_id` | UUID, FK | Account |
| `balance_amount` | Numeric, nullable | 当前余额 |
| `credit_limit` | Numeric, nullable | 总额度 |
| `remaining_credit` | Numeric, nullable | 剩余额度 |
| `currency` | String(16), nullable | 币种 |
| `expires_at` | DateTime, nullable | 额度到期时间 |
| `source` | String(32) | `provider_api` 或 `manual` |
| `collected_at` | DateTime | 采集时间 |

### 10.7 `api_health_checks`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `account_id` | UUID, FK | Account |
| `credential_id` | UUID, FK, nullable | 使用的 Credential |
| `check_type` | String(32) | `credential`、`models`、`balance`、`usage` |
| `status` | String(32) | `healthy`、`degraded`、`failed` |
| `latency_ms` | Integer, nullable | 延迟 |
| `error_code` | String(64), nullable | 稳定错误码 |
| `error_message` | String(512), nullable | 清洗后的错误 |
| `checked_at` | DateTime | 检测时间 |

### 10.8 `api_sync_runs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID | 主键 |
| `account_id` | UUID, FK | Account |
| `sync_type` | String(32) | `models`、`usage`、`balance`、`all` |
| `status` | String(32) | `queued`、`running`、`completed`、`partial`、`failed` |
| `requested_by_user_id` | UUID, FK, nullable | 手工触发用户；定时任务为空 |
| `started_at` | DateTime, nullable | 开始时间 |
| `completed_at` | DateTime, nullable | 完成时间 |
| `records_written` | Integer | 写入记录数量 |
| `error_code` | String(64), nullable | 稳定错误码 |
| `error_message` | String(512), nullable | 清洗后的错误 |
| `details` | JSON | 不含敏感值的执行摘要 |

## 11. 与现有表的关系

现有 `api_endpoints` 表与 `deployments` 一对一绑定，应继续表示本地 Deployment Endpoint，不应改造成外部 API Account 表。

原因：

- 本地 Endpoint 由 Deployment 生命周期自动创建和销毁。
- 外部 Account 独立存在，不属于任何 Server 或 Deployment。
- 外部 Credential、账单和模型发现需要独立权限和审计。
- 强行复用会产生大量 nullable 字段和不清晰的删除语义。

总览层可以通过 Service Projection 合并两类数据，但存储层保持独立。

## 12. Provider Adapter 设计

### 12.1 接口

```python
class ProviderAdapter(Protocol):
    slug: str
    capabilities: ProviderCapabilities

    async def validate_credential(self, context: ProviderContext) -> ValidationResult: ...
    async def list_models(self, context: ProviderContext) -> list[ProviderModel]: ...
    async def fetch_balance(self, context: ProviderContext) -> BalanceResult | None: ...
    async def fetch_usage(self, context: ProviderContext, period: TimeRange) -> UsageResult: ...
```

`ProviderContext` 只能由 Service 层创建，包含经过解密的临时 Credential、校验后的 Base URL、超时和代理配置。不得将该对象序列化、记录日志或放入 RQ Job 参数。

### 12.2 能力声明

```python
class ProviderCapabilities(BaseModel):
    credential_validation: bool
    model_discovery: bool
    balance_sync: bool
    usage_sync: bool
    usage_by_model: bool
    usage_by_credential: bool
    manual_usage_import: bool
```

前端必须根据能力声明显示操作，不得假设每个平台都支持余额和用量 API。

### 12.3 首版 Adapter

建议实施顺序：

1. `generic-openai`
   - 支持 Base URL、Bearer Token、`/models` 检测。
   - 不承诺余额和用量同步。
2. `openai`
   - 独立适配 Credential 验证、模型发现和可用的组织用量能力。
3. `anthropic`
   - 独立认证头和模型能力。
4. `aliyun-bailian`
   - 面向当前阿里云资源需求。
5. 其他 Provider
   - 按实际账号优先级增加，不提前做空壳 Adapter。

具体供应商接口可能变化，Adapter 必须有独立测试、超时和错误映射，不应把供应商响应直接暴露给前端。

## 13. 用量数据策略

### 13.1 数据来源优先级

1. Provider 官方 Usage/Billing API。
2. Provider 导出的账单文件。
3. Admin 人工录入。

每条数据必须记录 `source`，前端不能把人工数据和 Provider 数据混为一谈。

### 13.2 准确性边界

因为本模块不代理业务请求，所以：

- 无法通过本系统自动计算所有外部调用请求。
- 只有 Provider 提供 Usage API 时，才能自动同步完整或接近完整的数据。
- Provider 不提供 Usage API 时，只能展示人工维护或账单导入数据。
- 控制台自身的测试请求可以审计，但不应被当作该 Account 的全部用量。

### 13.3 时间与币种

- 数据库存储 UTC 时间。
- 前端根据用户时区展示。
- 同一图表默认只聚合相同币种。
- 多币种总览必须分组展示，首版不自动进行汇率换算。
- Provider 返回累计值时，Adapter 负责转换为可去重的周期快照。

### 13.4 数据保留

建议默认：

- 小时粒度：保留 90 天。
- 日粒度：保留 2 年。
- 月粒度：长期保留。
- Sync Run：保留 1 年。
- Health Check：保留 90 天。

保留策略应通过配置调整，并由 Worker 定时清理。

## 14. Credential 加密与密钥管理

### 14.1 主密钥

新增生产环境变量：

```text
AI_INFRA_CREDENTIAL_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
AI_INFRA_CREDENTIAL_ENCRYPTION_KEY_VERSION=v1
```

要求：

- 生产环境必须配置。
- 不得与 JWT Secret 或数据库密码复用。
- 不得提交到 Git。
- 应存放在系统 Secret Manager、受限环境文件或容器 Secret 中。

### 14.2 加密方案

- 使用经过认证的对称加密，例如 AES-256-GCM。
- 每条 Credential 使用独立随机 nonce。
- 将 Account ID、Credential ID 和 Key Version 作为 AAD。
- 数据库存储版本、nonce、ciphertext 和认证标签。
- 使用 HMAC-SHA-256 生成不可逆 fingerprint，用于重复检测。

### 14.3 解密边界

- 仅 Provider Adapter 调用期间解密。
- 解密值只存在于当前进程内存。
- 不进入 Redis、RQ 参数、日志、异常和审计详情。
- Worker Job 只接收 `account_id` 和 `sync_run_id`，由 Worker 自行从数据库读取并解密。

### 14.4 密钥轮换

支持双版本轮换：

1. 新增 `v2` 主密钥。
2. 新写入使用 `v2`。
3. 后台任务逐条解密 `v1` 并重新加密为 `v2`。
4. 确认无 `v1` 数据后移除旧密钥。

## 15. 网络与 SSRF 安全

外部 Base URL 会导致 Central 或 Worker 发起出站请求，必须防止 SSRF。

### 15.1 基本规则

- 生产环境默认只允许 HTTPS。
- 禁止 URL 中包含用户名或密码。
- 禁止非 HTTP(S) scheme。
- 禁止重定向到未授权地址。
- 限制响应大小、连接超时和总超时。
- 不下载任意文件。
- Adapter 只能访问固定、类型化的路径。
- 不提供“输入 URL 和 Method 后发送请求”的通用接口。

### 15.2 私有地址

自定义本地 API 可能位于私有网络，因此不能简单禁止全部私网地址。

新增配置：

```text
AI_INFRA_EXTERNAL_API_ALLOW_PRIVATE_NETWORKS=false
AI_INFRA_EXTERNAL_API_ALLOWED_HOSTS=[]
AI_INFRA_EXTERNAL_API_ALLOWED_CIDRS=[]
```

规则：

- 默认拒绝 loopback、link-local、metadata 地址和私有网络。
- Admin 可通过部署配置显式允许特定 Host 或 CIDR。
- 云 metadata 地址始终禁止。
- DNS 解析前后都要校验，防止 DNS rebinding。

## 16. 后端 API 设计

所有路由位于 `/api/v1/api-resources`，使用现有 JWT、Admin/Viewer 权限、请求 ID、错误 Envelope 和审计机制。

### 16.1 Provider

```http
GET /api/v1/api-resources/providers
GET /api/v1/api-resources/providers/{provider_slug}
```

返回 Provider 展示信息和能力，不返回 Credential。

### 16.2 Account

```http
GET    /api/v1/api-resources/accounts
POST   /api/v1/api-resources/accounts
GET    /api/v1/api-resources/accounts/{account_id}
PATCH  /api/v1/api-resources/accounts/{account_id}
POST   /api/v1/api-resources/accounts/{account_id}/archive
POST   /api/v1/api-resources/accounts/{account_id}/restore
```

列表查询支持：

- `provider`
- `status`
- `tag`
- `owner`
- `search`
- `include_archived`

### 16.3 Credential

```http
GET    /api/v1/api-resources/accounts/{account_id}/credentials
POST   /api/v1/api-resources/accounts/{account_id}/credentials
PATCH  /api/v1/api-resources/credentials/{credential_id}
POST   /api/v1/api-resources/credentials/{credential_id}/rotate
POST   /api/v1/api-resources/credentials/{credential_id}/validate
POST   /api/v1/api-resources/credentials/{credential_id}/disable
DELETE /api/v1/api-resources/credentials/{credential_id}
```

Credential Response 示例：

```json
{
  "id": "uuid",
  "name": "Research key",
  "credential_type": "api_key",
  "masked_value": "sk-****abcd",
  "status": "active",
  "expires_at": null,
  "last_validated_at": "2026-08-10T03:00:00Z",
  "last_error": null
}
```

### 16.4 Model

```http
GET  /api/v1/api-resources/accounts/{account_id}/models
POST /api/v1/api-resources/accounts/{account_id}/models/sync
POST /api/v1/api-resources/accounts/{account_id}/models/manual
```

### 16.5 Usage 与 Balance

```http
GET  /api/v1/api-resources/accounts/{account_id}/usage
GET  /api/v1/api-resources/accounts/{account_id}/balance
POST /api/v1/api-resources/accounts/{account_id}/usage/sync
POST /api/v1/api-resources/accounts/{account_id}/balance/sync
POST /api/v1/api-resources/accounts/{account_id}/usage/manual
GET  /api/v1/api-resources/usage/summary
```

Usage 查询参数：

- `date_from`
- `date_to`
- `granularity`
- `model`
- `credential_id`
- `source`

### 16.6 Sync Run

```http
GET  /api/v1/api-resources/accounts/{account_id}/sync-runs
GET  /api/v1/api-resources/sync-runs/{sync_run_id}
POST /api/v1/api-resources/accounts/{account_id}/sync
```

同步请求只允许枚举值：

```json
{
  "sync_types": ["models", "balance", "usage"]
}
```

## 17. 服务层与 Worker

建议模块结构：

```text
apps/api/src/ai_infra_api/
  api/api_resources.py
  schemas/api_resources.py
  services/api_resources/
    accounts.py
    credentials.py
    encryption.py
    health.py
    usage.py
    sync.py
    network_policy.py
    adapters/
      base.py
      registry.py
      generic_openai.py
      openai.py
      anthropic.py
      aliyun_bailian.py
```

Worker 任务必须是注册函数：

```python
sync_api_account_models(account_id, sync_run_id)
sync_api_account_balance(account_id, sync_run_id)
sync_api_account_usage(account_id, sync_run_id, period_start, period_end)
validate_api_credential(credential_id, sync_run_id)
prune_api_resource_history()
```

不得把明文 Credential 放入 Job 参数。

### 17.1 并发控制

- 同一 Account、同一 Sync Type 同时只能运行一个任务。
- 使用数据库状态与 Redis Job ID 防止重复执行。
- 手工触发和定时任务共享相同锁。
- 超时任务必须可标记为失败并释放租约。

### 17.2 重试

- 认证失败不自动重试。
- 429 按 Provider Retry-After 或指数退避重试。
- 5xx 和网络超时有限次数重试。
- 配置错误和 SSRF 拒绝不重试。
- 错误写入稳定 `error_code`，供应商原始响应不得完整保存。

## 18. 定时同步

首版建议：

- Credential 验证：每天一次。
- 模型同步：每天一次或手动触发。
- Balance 同步：每小时一次。
- Usage 同步：每天同步最近 7 天，处理供应商延迟修正。
- 历史清理：每天一次。

Account 可覆盖默认周期，但必须设置最小间隔，防止滥用供应商 API。

建议新增配置：

```text
AI_INFRA_API_RESOURCE_SYNC_ENABLED=true
AI_INFRA_API_RESOURCE_VALIDATION_INTERVAL_SECONDS=86400
AI_INFRA_API_RESOURCE_MODEL_SYNC_INTERVAL_SECONDS=86400
AI_INFRA_API_RESOURCE_BALANCE_SYNC_INTERVAL_SECONDS=3600
AI_INFRA_API_RESOURCE_USAGE_SYNC_INTERVAL_SECONDS=86400
AI_INFRA_API_RESOURCE_REQUEST_TIMEOUT_SECONDS=15
AI_INFRA_API_RESOURCE_MAX_RESPONSE_BYTES=2097152
```

## 19. 审计事件

新增事件：

```text
api_resource.account.created
api_resource.account.updated
api_resource.account.archived
api_resource.account.restored
api_resource.credential.created
api_resource.credential.rotated
api_resource.credential.validated
api_resource.credential.disabled
api_resource.credential.deleted
api_resource.models.synced
api_resource.balance.synced
api_resource.usage.synced
api_resource.usage.manual_created
api_resource.sync.failed
```

审计详情允许记录：

- Account ID。
- Provider slug。
- Credential ID。
- Credential 掩码。
- Sync Run ID。
- 结果和安全错误码。

禁止记录：

- 明文 Credential。
- Authorization Header。
- Provider 完整错误响应。
- 请求 Prompt 或模型输出。

## 20. 通知规则

建议新增派生通知：

- Credential 验证失败。
- Credential 7 天内到期。
- Account 连续三次同步失败。
- Balance 低于人工阈值。
- 月费用达到预算的 80%、95% 和 100%。
- Usage 数据超过允许的新鲜度。
- Provider Adapter 被禁用。

通知去重键应包含 Account ID、通知类型和时间窗口。

## 21. 前端实现

建议目录：

```text
apps/web/src/
  app/(console)/api-resources/
  features/api-resources/
  components/api-resources/
  hooks/use-api-resources.ts
  lib/api/api-resources.ts
```

### 21.1 BFF 路由

浏览器仍通过 Same-Origin BFF，不直接持有 Central Bearer Token。

```text
/api/api-resources/providers
/api/api-resources/accounts
/api/api-resources/accounts/[id]
/api/api-resources/accounts/[id]/credentials
/api/api-resources/accounts/[id]/models
/api/api-resources/accounts/[id]/usage
/api/api-resources/accounts/[id]/sync
```

### 21.2 数据获取

- 使用 TanStack Query。
- Query Key 包含筛选条件和时间范围。
- Credential Mutation 成功后立即清空表单中的明文值。
- 禁止把 Credential 写入 Zustand、localStorage、URL、日志或 Toast。
- Usage 图表明确显示数据来源和最近同步时间。

### 21.3 空状态

- 没有 External Account：引导 Admin 新建，Viewer 显示只读说明。
- Provider 不支持 Usage：显示能力限制，不显示错误状态。
- 尚未同步：显示 `Never synced`。
- 数据过期：显示新鲜度警告。

## 22. API 错误码

建议稳定错误码：

```text
api_provider_not_found
api_provider_disabled
api_account_not_found
api_account_archived
api_account_name_conflict
api_credential_not_found
api_credential_required
api_credential_invalid
api_credential_expired
api_credential_duplicate
api_credential_encryption_failed
api_provider_capability_unsupported
api_provider_rate_limited
api_provider_timeout
api_provider_unavailable
api_provider_response_invalid
api_base_url_not_allowed
api_sync_already_running
api_sync_not_found
api_usage_period_invalid
api_usage_import_invalid
```

## 23. 测试策略

### 23.1 后端单元测试

- Credential 加密、解密和 Key Version。
- Fingerprint 重复检测。
- 掩码生成。
- Base URL 标准化。
- SSRF 与 CIDR 策略。
- Provider 错误映射。
- Usage 去重和聚合。
- 多币种分组。
- 权限与审计。

### 23.2 Adapter 测试

- 使用 `httpx.MockTransport`，不访问真实供应商。
- 覆盖成功、401、403、404、429、5xx、超时和无效 JSON。
- 验证日志不包含 Credential。
- 验证重定向不会绕过 Host/CIDR 策略。

### 23.3 API 测试

- Admin CRUD。
- Viewer 只读限制。
- Credential Response 不返回明文。
- 归档 Account 不允许同步。
- 重复同步冲突。
- Usage 时间范围校验。
- 稳定错误 Envelope 和 Request ID。

### 23.4 Worker 测试

- Job 只接收 ID，不接收 Credential。
- 同一 Account 的同步互斥。
- 重试策略。
- 失败任务状态回收。
- 数据去重。

### 23.5 Web 测试

- Provider Capability 控制按钮显示。
- Credential 表单清理。
- Viewer 不显示写操作。
- Usage 来源和新鲜度显示。
- Account 筛选和空状态。
- 移动端和窄屏布局。

### 23.6 安全扫描

扩展 `scripts/security_scan.py`：

- 检查测试 Fixture 之外是否出现真实 Key 格式。
- 检查 API Response Schema 是否包含 `encrypted_value`。
- 检查日志调用是否传入 Credential 字段。
- 检查新增路由是否包含通用 URL、Method 和 Header 转发组合。

## 24. 数据迁移与兼容

### 24.1 Migration

新增独立 Alembic Migration：

- 创建 API Resource 相关表。
- 创建唯一约束和时间查询索引。
- 不修改现有 Deployment 和 `api_endpoints` 语义。
- Migration 必须支持 downgrade。

### 24.2 路由兼容

- 保留 `/apis`，重定向到本地推理 API 页面。
- 现有 Deployment Test API 保持不变。
- 不改变 Agent 协议。
- 外部 Credential 只保存在 Central，不下发 Agent。

## 25. 分阶段实施计划

### Phase 10A：资产台账基础

范围：

- Provider Registry。
- Account CRUD。
- Credential 加密保存、掩码和轮换。
- Generic OpenAI-compatible Credential 验证。
- 外部 API 列表和详情页。
- Admin/Viewer 权限和审计。

验收：

- Admin 可安全登记外部 API Account。
- 数据库、API、日志和前端不泄露明文 Credential。
- Viewer 只能查看掩码和状态。
- 自定义 Base URL 通过 SSRF 策略校验。

### Phase 10B：模型与健康

范围：

- Provider Adapter Registry。
- 模型发现。
- Credential 定时验证。
- Health Check 历史。
- 失效和到期通知。

验收：

- 支持的 Provider 能同步模型。
- 不支持模型发现的平台允许人工维护。
- 健康状态有最近检测时间和安全错误。

### Phase 10C：余额与用量

范围：

- Balance Snapshot。
- Usage Snapshot。
- Usage/Balance Adapter。
- 人工录入与账单导入基础。
- 用量和费用图表。

验收：

- 每条数据明确来源。
- 重复同步不产生重复记录。
- 多币种不错误合计。
- Provider 不支持 Usage 时显示能力限制。

### Phase 10D：运营完善

范围：

- 定时同步。
- 预算与余额通知。
- 数据保留任务。
- CSV 导出。
- Dashboard 摘要。
- Provider 扩展。

验收：

- 自动同步失败可观察、可重试、可审计。
- 导出不包含 Credential。
- 通知去重有效。

## 26. 完成定义

模块达到 Complete 需要同时满足：

- 数据模型、Migration、API、Worker 和 Web 页面实现完成。
- Credential 使用独立生产加密密钥。
- 至少实现 `generic-openai` 和一个真实外部 Provider Adapter。
- Provider 能力差异在前端正确呈现。
- Usage 数据来源和准确性边界清晰。
- Admin/Viewer 权限测试完整。
- SSRF、日志脱敏和 Credential 泄漏测试通过。
- API、Web、Worker、Migration 和安全扫描全部通过。
- 中文 README、Roadmap 和部署环境变量文档更新。
- 生产升级和回滚步骤完成验证。

## 27. 运维要求

- 备份数据库前确认 Credential 密文和主密钥分别保管。
- 数据库备份不应包含主密钥。
- 丢失主密钥后 Credential 无法恢复，只能重新录入。
- 轮换主密钥前必须完成可恢复备份。
- Worker 必须能够访问允许的 Provider 网络地址。
- 代理环境变量应由部署配置提供，不写入 Account Notes。
- 同步任务的超时、速率限制和错误率应进入日志与监控。

## 28. 开发前待确认项

开始编码前需要由产品负责人确认：

1. 首批必须支持的 Provider 排序。
2. 是否需要一个 Account 配置多个 Credential。
3. 是否需要人工账单 CSV 导入。
4. 是否需要预算和余额阈值通知。
5. 自定义私网 Base URL 的允许范围。
6. 默认用量保留周期。
7. 是否允许 Viewer 查看费用。
8. 是否需要负责人字段关联现有 User，还是首版使用普通文本。
9. 是否需要对接 CCSwitch 配置导入；如需要，仅做配置导入，不做客户端远程控制。

在以上问题未全部确认前，Phase 10A 仍可先实现 Provider Registry、Account、Credential Encryption、RBAC 和 Generic OpenAI-compatible 验证。
