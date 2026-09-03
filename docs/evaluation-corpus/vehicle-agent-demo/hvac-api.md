# 空调接口（虚构 Demo）

示例 `HvacService.setTemperature` 请求包含 `requestId`、`zone`、`temperatureCelsius`。zone 可为 `driver`、`passenger`、`rear`；双区模式必须分别传入 driver 或 passenger，不能用一个全局温度覆盖两个分区。

服务返回 `accepted`、`appliedTemperatureCelsius` 和可选错误码。服务端响应超时不代表车辆没有执行：客户端先按 requestId 查询最近结果，再以指数退避重试一次；没有幂等 requestId 时不得盲目重试。
