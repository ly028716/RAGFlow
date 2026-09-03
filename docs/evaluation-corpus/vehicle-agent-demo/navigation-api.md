# 导航接口（虚构 Demo）

示例 `Navigation.routeTo` 接收 destination、requestId 和 profile。路线状态为 `ROUTING`、`READY`、`NO_FIX`、`NETWORK_UNAVAILABLE`、`FAILED`。

定位异常首先检查定位状态是否为 NO_FIX、最近 GNSS/定位日志和请求参数；网络异常时为 NETWORK_UNAVAILABLE，不应误报为路线计算失败。失败响应必须保留 requestId，便于关联日志。
