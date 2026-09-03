# V1/V2 版本差异（虚构 Demo）

空调 V1 的 `setTemperature` 使用 `temperatureCelsius` 和单一 `zone`。V2 保留这两个字段，并新增 `syncGroupId`，用于明确多个分区是否同步；V1 客户端不发送该字段时，V2 服务按单区语义处理。

车控 V2 响应增加 `appliedAtEpochMs` 与 `retryAfterMs`。V1 客户端应忽略未知响应字段；V2 客户端调用旧服务时不得依赖新增字段，并应回退到 requestId 查询策略。
