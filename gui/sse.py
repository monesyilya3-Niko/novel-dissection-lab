"""SSE（Server-Sent Events）进度推送工具。

基于标准库 http.server 的分块写能力，向前端 EventSource 推送 progress 事件。
协议：``text/event-stream``，每条消息 ``data: <json>\\n\\n``。
"""
from __future__ import annotations

import json
import queue
import threading
from typing import Any


class SseBroker:
    """线程安全的事件分发器：服务层往队列塞事件，每个 SSE 连接各自消费。

    采用「每连接一个 queue」的广播模型：发布时向所有活跃连接投递；连接关闭时
    自动移除，并设置最大订阅者上限（超出时淘汰最老连接队列），避免半开连接无限堆积。
    """

    MAX_SUBSCRIBERS = 64

    def __init__(self, max_subscribers: int = MAX_SUBSCRIBERS) -> None:
        self.max_subscribers = max(1, int(max_subscribers))
        self._subscribers: dict[queue.Queue, None] = {}
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        """注册一个新订阅者，返回其专属队列；若达到上限则淘汰最老队列。"""
        q: queue.Queue = queue.Queue(maxsize=256)
        with self._lock:
            while len(self._subscribers) >= self.max_subscribers:
                oldest = next(iter(self._subscribers))
                self._subscribers.pop(oldest, None)
            self._subscribers[q] = None
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        """移除订阅者。"""
        with self._lock:
            self._subscribers.pop(q, None)

    def publish(self, event: dict[str, Any]) -> None:
        """向所有活跃订阅者广播一个事件（非阻塞投递）。"""
        with self._lock:
            subs = list(self._subscribers.keys())
        for q in subs:
            try:
                q.put_nowait(event)
            except queue.Full:
                # 队列满（订阅者消费太慢），丢弃以避免阻塞服务层。
                continue


def format_event(event: dict[str, Any]) -> str:
    """把一个事件 dict 序列化为 SSE 帧。

    ⚠️ 返回的是 str，调用方编码成 UTF-8 时必须用 ``errors="replace"``：
    事件里可能带用户数据，孤立代理字符（U+D800–U+DFFF）无法编码。
    server.py 的 SSE 写入点已经这么做了（2026-11-07）。
    """
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# 全局单例 broker（服务层与 server 共用）。
broker = SseBroker()
