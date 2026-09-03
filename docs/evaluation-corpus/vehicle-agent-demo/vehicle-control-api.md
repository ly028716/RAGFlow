# 车控接口（虚构 Demo）

示例 `VehicleControl.setWindow` 请求包含 `requestId`、`zone`、`positionPercent` 和 `callerToken`。`zone` 取 `front_left`、`front_right`、`rear_left` 或 `rear_right`；`positionPercent` 范围是 0 到 100。

服务校验 callerToken 的车控权限和 zone 合法性，再写入车辆属性。响应包含 `requestId`、`status` 和可选 `errorCode`。请求必须幂等：同一 requestId 重试不得重复执行。

普通第三方应用不可直接调用门锁、车窗等控制接口；这类能力仅向受信任系统组件开放，并必须审计调用主体与结果。
