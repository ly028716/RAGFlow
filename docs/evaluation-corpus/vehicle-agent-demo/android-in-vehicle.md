# 车载 Android 系统说明（虚构 Demo）

示例座舱使用 Android Automotive 风格的分层。`CarService` 向受信任的系统组件提供车辆属性、用户和音频策略服务；普通应用不能获得受限车辆属性的写权限。

系统启动时先启动 system_server，再初始化 CarService，最后由应用绑定领域服务。若 CarService 未就绪，应用应显示服务初始化中，不应缓存一次失败后永久不可用的状态。

诊断时优先检查 `ActivityManager`、`CarService` 和领域服务的同一时间窗口日志，并记录系统版本与车辆配置版本。
