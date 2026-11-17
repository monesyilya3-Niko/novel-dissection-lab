-- 0005: 伏笔回收链持久化显露章字段（reveal_chapter）
-- 修复此前仅在内存格式化层回显 reveal_chapter、刷新页面后退回 (hook + payoff) // 2 的丢失缺陷。

ALTER TABLE essence_chains ADD COLUMN reveal_chapter INTEGER;
