// 题材推断工具（WS-A3 Smart Defaults）：基于文件名/样章文本的关键词匹配，无依赖。
// 关键词映射覆盖 48 个 KNOWN_GENRES 中的主要高频题材（≥15），来自 gui/scripts/genre_registry.py 派生。

export const GENRE_KEYWORDS: Record<string, string[]> = {
  // 校园 / 青春
  'campus-redemption': ['校园', '学霸', '学园', '校草', '救赎', '校园救赎'],
  'qingchun-xiaoyuan': ['青春', '初恋', '同桌', '校花'],
  'qingchun-tianchong': ['甜宠', '宠文', '甜文'],

  // 仙侠 / 玄幻 / 奇幻
  'xianxia': ['仙侠', '修真', '修仙', '渡劫', '御剑', '宗门', '仙尊', '飞升', '金丹', '元婴'],
  'xuanhuan': ['玄幻', '斗破', '武魂', '斗罗', '斗气', '魂兽', '至尊', '玄幻'],
  'xuanhuan-naodong': ['玄幻脑洞'],
  'xifang-qihuan': ['西幻', '奇幻', '魔法', '精灵', '法师', '巫师', '龙骑士', '奇幻'],
  'wuxia-chuantong': ['武侠', '江湖', '剑客', '侠客', '武林', '华山', '武当'],
  'wuxianliu': ['无限流', '副本', '主神', '轮回', '轮回者'],

  // 都市系（高武/修真/系统/神医/种田/脑洞/兵王/赘婿）
  'dushi-gaowu': ['都市', '高武', '气血', '武道'],
  'dushi-xiuzhen': ['都市修真', '都市修仙'],
  'dushi-shenyi': ['神医', '圣手', '医术', '神针'],
  'dushi-zhongtian': ['都市种田', '灵泉', '空间种田'],
  'dushi-xitong': ['系统', '签到', '奖励', '任务发布', '签到系统'],
  'dushi-naodong': ['都市脑洞', '沙雕', '整活'],
  'dushi-bingwang': ['兵王', '特种兵', '退役兵王', '雇佣兵'],
  'zhanshen-zhuixu': ['战神', '赘婿', '上门女婿', '龙王', '龙帅'],
  'dushi-richang': ['都市日常', '日常文'],
  'zhichang-hunlian': ['职场', '婚恋', '职场婚恋'],

  // 宫斗 / 豪门 / 古风
  'gongdou': ['宫斗', '嫔妃', '皇后', '后宫', '太后'],
  'haomen-zongcai': ['豪门', '总裁', '霸总', '契约婚姻'],
  'gufeng-shiqing': ['古风', '世情'],
  'guyan-naodong': ['古言脑洞'],
  'minguo-yanqing': ['民国', '民国言情'],
  'niandai': ['年代', '年代文'],

  // 科幻
  'kehuan-moshi': ['末世', '丧尸', '末日', '废土'],
  'kehuan-xingji': ['星际', '机甲', '星舰', '虫族', '星际'],

  // 历史 / 穿越
  'lishi': ['历史', '三国', '大明', '大唐', '大秦'],
  'lishi-chuanyue': ['历史穿越', '穿越古代', '穿越回'],
  'kuaichuan': ['快穿', '宿主', '攻略', '穿书'],

  // 悬疑 / 灵异 / 盗墓 / 刑侦
  'xuanyi-lingyi': ['灵异', '捉鬼', '驱邪', '阴魂', '灵异'],
  'xuanyi-daomu': ['盗墓', '古墓', '摸金', '下墓', '盗墓笔记'],
  'xuanyi-xingzhen': ['刑侦', '探案', '悬疑刑侦'],
  'xuanyi-naodong': ['悬疑脑洞'],

  // 游戏 / 电竞
  'youxi-wangyou': ['网游', '游戏', '公会', '打怪', '副本', '升级'],
  'youxi-tiyu': ['体育', '竞技'],
  'dianjing': ['电竞', '战队', '选手', '夺冠', '联赛', '电竞'],

  // 言情 / 重生 等细分
  'realistic-romance': ['现实言情', '言情'],
  'zhongtian': ['种田', '田园', '灵田', '种田文'],
  'meishi': ['美食', '美食文', '烹饪'],
  'nvpin-zhongtian': ['女频种田'],
  'xianyan-naodong': ['现言脑洞'],
}

function scoreText(lowerText: string, genres: string[]): { best: string | null; bestScore: number } {
  if (!lowerText || !genres.length) return { best: null, bestScore: 0 }
  let best: string | null = null
  let bestScore = 0
  for (const g of genres) {
    const kws = GENRE_KEYWORDS[g]
    if (!kws || kws.length === 0) continue
    let s = 0
    for (const kw of kws) {
      if (lowerText.includes(kw.toLowerCase())) s += 1
    }
    if (s > bestScore) {
      bestScore = s
      best = g
    }
  }
  return { best, bestScore }
}

/** 基于文件名推断题材；大小写不敏感；仅返回在 genres 白名单中的 slug。 */
export function inferGenreFromFilename(filename: string, genres: string[]): string | null {
  if (!filename || !genres?.length) return null
  const lower = filename.toLowerCase()
  const { best, bestScore } = scoreText(lower, genres)
  return bestScore > 0 ? best : null
}

/** 基于样章正文预览推断题材；大小写不敏感；仅返回在 genres 白名单中的 slug。 */
export function inferGenreFromText(sampleText: string, genres: string[]): string | null {
  if (!sampleText || !genres?.length) return null
  const lower = sampleText.toLowerCase()
  const { best, bestScore } = scoreText(lower, genres)
  return bestScore > 0 ? best : null
}
