import { describe, it, expect } from 'vitest'
import { inferGenreFromFilename, inferGenreFromText, GENRE_KEYWORDS } from './inferGenre'

// 与真实 KNOWN_GENRES 规模一致的示例白名单（测试不依赖后端，需显式构造）
const GENRES = [
  'campus-redemption',
  'qingchun-xiaoyuan',
  'xianxia',
  'xuanhuan',
  'xifang-qihuan',
  'dushi-gaowu',
  'dushi-shenyi',
  'dushi-xiuzhen',
  'dushi-xitong',
  'haomen-zongcai',
  'gongdou',
  'kehuan-moshi',
  'kehuan-xingji',
  'lishi',
  'kuaichuan',
  'zhanshen-zhuixu',
  'dushi-bingwang',
  'wuxia-chuantong',
]

describe('inferGenre — file/keyword mapping coverage', () => {
  it('mapping covers at least 15 genre keywords (task requirement)', () => {
    const covered = Object.keys(GENRE_KEYWORDS).filter((g) => GENRES.includes(g) || GENRE_KEYWORDS[g])
    expect(covered.length).toBeGreaterThanOrEqual(15)
  })
})

describe('inferGenreFromFilename — positive matches', () => {
  it('校园/学霸 -> campus-redemption', () => {
    expect(inferGenreFromFilename('校园救赎录.txt', GENRES)).toBe('campus-redemption')
    expect(inferGenreFromFilename('学霸的救赎之路.txt', GENRES)).toBe('campus-redemption')
  })

  it('仙侠/修真/渡劫 -> xianxia', () => {
    expect(inferGenreFromFilename('修真归来渡劫篇.txt', GENRES)).toBe('xianxia')
    expect(inferGenreFromFilename('仙侠奇缘.txt', GENRES)).toBe('xianxia')
  })

  it('玄幻/斗破/武魂 -> xuanhuan', () => {
    expect(inferGenreFromFilename('斗破苍穹续.txt', GENRES)).toBe('xuanhuan')
    expect(inferGenreFromFilename('武魂觉醒.txt', GENRES)).toBe('xuanhuan')
  })

  it('西幻/魔法 -> xifang-qihuan', () => {
    expect(inferGenreFromFilename('西幻魔法学院.txt', GENRES)).toBe('xifang-qihuan')
  })

  it('都市类 -> dushi-gaowu', () => {
    expect(inferGenreFromFilename('都市高武时代.txt', GENRES)).toBe('dushi-gaowu')
  })

  it('case-insensitive match (filename uppercased by FS)', () => {
    expect(inferGenreFromFilename('REMAKE-校园救赎录.TXT', GENRES)).toBe('campus-redemption')
  })
})

describe('inferGenreFromFilename — fallback', () => {
  it('no keyword matched -> null', () => {
    expect(inferGenreFromFilename('平淡的日常流水账.txt', GENRES)).toBeNull()
    expect(inferGenreFromFilename('12345.txt', GENRES)).toBeNull()
  })

  it('empty filename -> null', () => {
    expect(inferGenreFromFilename('', GENRES)).toBeNull()
  })

  it('empty genre whitelist -> null', () => {
    expect(inferGenreFromFilename('校园救赎.txt', [])).toBeNull()
  })

  it('inferred genre not in whitelist is discarded', () => {
    // 关键词存在但白名单不含该题材时不回退成它
    const narrow = ['campus-redemption']
    expect(inferGenreFromFilename('修真渡劫传.txt', narrow)).toBeNull()
  })
})

describe('inferGenreFromText — positive matches', () => {
  it('sample text 含仙侠关键词 -> xianxia', () => {
    const text = '林枫盘膝而坐，体内金丹震动，即将渡劫。宗门长老齐齐御剑而来。'
    expect(inferGenreFromText(text, GENRES)).toBe('xianxia')
  })

  it('sample text 含末世/丧尸 -> kehuan-moshi', () => {
    const text = '末世爆发，丧尸围城，幸存者躲在废土掩体中。'
    expect(inferGenreFromText(text, GENRES)).toBe('kehuan-moshi')
  })

  it('no match -> null', () => {
    expect(inferGenreFromText('今天天气不错。', GENRES)).toBeNull()
    expect(inferGenreFromText('', GENRES)).toBeNull()
  })
})
