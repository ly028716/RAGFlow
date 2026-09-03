# Android 车机日志诊断（虚构 Demo）

诊断按同一时间窗口收集 `ActivityManager`、`CarService`、领域服务和网关日志。CarService 启动失败的示例信号是 `CarService: initialization failed`，随后可能有依赖服务未注册。

车控无响应时依次确认：应用是否收到响应、领域服务是否记录 requestId、是否有 `DeadObjectException`、车辆属性是否写入、网关是否报告总线超时。ANR 应同时查看主线程堆栈和 Binder 调用耗时。
