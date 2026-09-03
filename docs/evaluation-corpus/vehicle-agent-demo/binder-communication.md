# 车载 Binder 通信（虚构 Demo）

领域服务通过 AIDL 暴露 Binder 接口。客户端绑定后应注册 death recipient。收到 binderDied 回调时，客户端清空旧代理、取消未完成请求，并以有限次数重新绑定。

不要在 Binder 主线程执行网络或磁盘阻塞操作。服务端返回超时与 Binder 死亡是不同故障：前者仍可按 requestId 查询结果，后者必须重新建立连接后再决定是否恢复请求。
