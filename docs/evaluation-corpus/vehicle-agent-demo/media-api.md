# 媒体接口（虚构 Demo）

示例播放器状态为 `IDLE`、`BUFFERING`、`PLAYING`、`PAUSED`、`ERROR`。音频焦点暂时丢失时播放器进入 PAUSED；永久丢失时释放播放资源并等待用户再次发起播放。

播放失败先区分焦点与服务异常：存在 `AudioFocus` 丢失记录而媒体服务正常时优先处理焦点；若媒体服务 Binder 断开或出现 ERROR，则重新绑定服务并保留可恢复的播放位置。
