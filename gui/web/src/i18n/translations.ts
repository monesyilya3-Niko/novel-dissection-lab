// 中英文双语词条词典（暮冬念春 / Exoscribe 国际化架构）。
export type Locale = 'zh-CN' | 'en-US'
export type TranslationKey = string

export const TRANSLATIONS: Record<string, Record<Locale, string>> = {
  // 品牌与全局头部
  brand_name: {
    'zh-CN': '暮冬念春',
    'en-US': 'Exoscribe',
  },
  brand_subtitle: {
    'zh-CN': '全功能工作台',
    'en-US': 'The Vernal Engine for Fiction',
  },
  brand_initial: {
    'zh-CN': '暮',
    'en-US': 'E',
  },
  toggle_language: {
    'zh-CN': '切换为英文 (Switch to English)',
    'en-US': '切换为中文 (Switch to Chinese)',
  },
  toggle_theme_light: {
    'zh-CN': '切换暗色',
    'en-US': 'Switch to Dark Mode',
  },
  toggle_theme_dark: {
    'zh-CN': '切换为跟随系统',
    'en-US': 'Switch to System Mode',
  },
  toggle_theme_system: {
    'zh-CN': '切换亮色',
    'en-US': 'Switch to Light Mode',
  },
  command_palette_trigger: {
    'zh-CN': '命令面板 (Ctrl+K)',
    'en-US': 'Command Palette (Ctrl+K)',
  },

  nav_group_more: {
    'zh-CN': '更多工具',
    'en-US': 'More Tools',
  },
  // 导航分组
  nav_group_create: {
    'zh-CN': '创作',
    'en-US': 'Creation',
  },
  nav_group_manage: {
    'zh-CN': '管理',
    'en-US': 'Management',
  },
  nav_group_help: {
    'zh-CN': '帮助',
    'en-US': 'Help',
  },

  // 导航选项
  nav_home: {
    'zh-CN': '首页',
    'en-US': 'Home',
  },
  nav_analysis: {
    'zh-CN': '分析拆书',
    'en-US': 'Deconstruction',
  },
  nav_writing: {
    'zh-CN': '辅助写作',
    'en-US': 'Writing Studio',
  },
  nav_quality: {
    'zh-CN': '质量检验',
    'en-US': 'Quality Guard',
  },
  nav_assets: {
    'zh-CN': '资产库',
    'en-US': 'Asset Matrix',
  },
  nav_advanced: {
    'zh-CN': '高级功能',
    'en-US': 'Advanced Tools',
  },
  nav_system: {
    'zh-CN': '系统',
    'en-US': 'System',
  },
  nav_settings: {
    'zh-CN': '设置',
    'en-US': 'Settings',
  },
  nav_admin: {
    'zh-CN': '管理后台',
    'en-US': 'Administration',
  },
  nav_help: {
    'zh-CN': '帮助中心',
    'en-US': 'Help Center',
  },

  // 编辑器与底栏诊断
  editor_placeholder: {
    'zh-CN': '在此粘贴或编写章节正文……',
    'en-US': 'Paste or compose chapter draft here...',
  },
  editor_poison_check: {
    'zh-CN': '🛡️ 毒点避雷排查',
    'en-US': '🛡️ Anti-Poison Check',
  },
  editor_deslop_check: {
    'zh-CN': '✨ 去AI味体检',
    'en-US': '✨ Anti-Slop Audit',
  },
  editor_constitution_check: {
    'zh-CN': '📜 设定宪法审查',
    'en-US': '📜 Novel Constitution',
  },
  editor_close_return: {
    'zh-CN': '关闭并返回写作',
    'en-US': 'Close & Return',
  },
  editor_word_unit: {
    'zh-CN': '字',
    'en-US': 'words',
  },
  editor_target_met: {
    'zh-CN': '已达目标',
    'en-US': 'Target Reached',
  },
  editor_target_prefix: {
    'zh-CN': '目标',
    'en-US': 'Target',
  },
  editor_empty_text: {
    'zh-CN': '正文为空，请先编写章节内容',
    'en-US': 'Draft is empty. Please enter chapter text first.',
  },
  editor_poison_modal_title: {
    'zh-CN': '🛡️ 章节毒点排查诊断',
    'en-US': '🛡️ Chapter Anti-Poison Audit',
  },
  editor_poison_safe_alert: {
    'zh-CN': '本章未命中任何已知的过度憋屈、圣母资敌、降智舔狗、战力断崖等恶性弃坑毒点，行文节奏舒畅！',
    'en-US': 'No fatal reader-turnoff taboos (excessive frustration, enemy mercy, IQ drop, power cliffs) detected. Smooth narrative flow!',
  },
  editor_poison_issues_found: {
    'zh-CN': '检出 {count} 处潜在风险（扣分：{score}）：',
    'en-US': 'Found {count} potential risks (penalty score: {score}):',
  },
  editor_poison_line_chip: {
    'zh-CN': '第 {line} 行',
    'en-US': 'Line {line}',
  },
  editor_poison_matched: {
    'zh-CN': '命中：{matched}',
    'en-US': 'Matched: {matched}',
  },
  editor_poison_suggestion_label: {
    'zh-CN': '【改法建议】 {suggestion}',
    'en-US': '[Suggestion] {suggestion}',
  },
  editor_deslop_modal_title: {
    'zh-CN': '✨ 章节去 AI 味诊断',
    'en-US': '✨ Chapter Anti-Slop Audit',
  },
  editor_deslop_ai_score_chip: {
    'zh-CN': 'AI 指数: {score} ({verdict})',
    'en-US': 'AI Index: {score} ({verdict})',
  },
  editor_deslop_safe_alert: {
    'zh-CN': '正文行文极其自然，未检测到任何程式化套路、玄虚比喻、无由排比或俗套口癖！',
    'en-US': 'Prose flows naturally with no detected clichés, obscure metaphors, empty parallelism, or AI speech patterns!',
  },
  editor_deslop_issues_found: {
    'zh-CN': '检出 {count} 处模式化套路（总字数：{words}，总句数：{sents}，被动句让字密度：{density}‰）：',
    'en-US': 'Found {count} stylized patterns ({words} words, {sents} sentences, passive density: {density}‰):',
  },
  editor_deslop_weight_label: {
    'zh-CN': '扣分权重：{weight}',
    'en-US': 'Penalty Weight: {weight}',
  },
  editor_deslop_suggestion_label: {
    'zh-CN': '【优化建议】 {suggestion}',
    'en-US': '[Optimization Suggestion] {suggestion}',
  },
  editor_const_modal_title: {
    'zh-CN': '📜 章节设定与世界观宪法审查',
    'en-US': '📜 Novel Constitution & Canon Audit',
  },
  editor_const_score_chip: {
    'zh-CN': '合规得分: {score} ({status})',
    'en-US': 'Compliance Score: {score} ({status})',
  },
  editor_const_compliant: {
    'zh-CN': '正典合规',
    'en-US': 'Canon Compliant',
  },
  editor_const_risk: {
    'zh-CN': '存在违宪风险',
    'en-US': 'Canon Risk Detected',
  },
  editor_const_safe_alert: {
    'zh-CN': '全章设定完美合规，未触碰世界观红线，角色声线与行为严丝合缝！',
    'en-US': 'Chapter adheres perfectly to canon boundaries with no worldbuilding violations or out-of-character drift!',
  },
  editor_const_violations_title: {
    'zh-CN': '🚫 世界观违宪项 ({count})',
    'en-US': '🚫 Canon & Worldbuilding Violations ({count})',
  },
  editor_const_term_matched: {
    'zh-CN': '命中禁用词：【{term}】（第 {line} 行）',
    'en-US': 'Forbidden Term: [{term}] (Line {line})',
  },
  editor_const_voice_title: {
    'zh-CN': '🎭 角色声线脱缰警报 ({count})',
    'en-US': '🎭 Character Voice Taboo Alerts ({count})',
  },
  editor_const_voice_char: {
    'zh-CN': '角色: {character}',
    'en-US': 'Character: {character}',
  },
  editor_const_voice_forbidden: {
    'zh-CN': '说了禁说台词：【{phrase}】（第 {line} 行）',
    'en-US': 'Spoke Forbidden Taboo: [{phrase}] (Line {line})',
  },

  // 顶层全局与导航 (App & Navigation)
  app_init_failed: {
    'zh-CN': '初始化失败：{error}',
    'en-US': 'Initialization failed: {error}',
  },
  nav_open_drawer: {
    'zh-CN': '打开导航',
    'en-US': 'Open Navigation',
  },
  help_fab_tooltip: {
    'zh-CN': '帮助中心：术语、指南、工作流',
    'en-US': 'Help Center: Terms, Guides, Workflows',
  },
  help_fab_aria: {
    'zh-CN': '打开帮助中心',
    'en-US': 'Open Help Center',
  },

  // 通用动作与状态
  action_save: {
    'zh-CN': '保存',
    'en-US': 'Save',
  },
  action_cancel: {
    'zh-CN': '取消',
    'en-US': 'Cancel',
  },
  action_create: {
    'zh-CN': '创建',
    'en-US': 'Create',
  },
  action_creating: {
    'zh-CN': '创建中…',
    'en-US': 'Creating...',
  },
  action_confirm: {
    'zh-CN': '确定',
    'en-US': 'Confirm',
  },
  action_close: {
    'zh-CN': '关闭',
    'en-US': 'Close',
  },
  action_export: {
    'zh-CN': '导出',
    'en-US': 'Export',
  },
  action_import: {
    'zh-CN': '导入',
    'en-US': 'Import',
  },
  action_retry: {
    'zh-CN': '重试',
    'en-US': 'Retry',
  },
  action_search: {
    'zh-CN': '搜索',
    'en-US': 'Search',
  },

  // 平台与出海适配
  platform_panel_title: {
    'zh-CN': '多平台适配与签约诊断',
    'en-US': 'Multi-Platform Adaptation & Submission Audit',
  },
  platform_tab_diagnose: {
    'zh-CN': '多平台合规与签约诊断',
    'en-US': 'Platform Compliance & Submission Audit',
  },
  platform_tab_litrpg: {
    'zh-CN': 'LitRPG 属性面板与海外排版',
    'en-US': 'LitRPG Stat Box & Formatter',
  },
  platform_check_compliance: {
    'zh-CN': '检查合规性',
    'en-US': 'Check Compliance',
  },
  platform_diagnose_action: {
    'zh-CN': '🎯 签约过稿深度诊断',
    'en-US': '🎯 Submission Readiness Audit',
  },
  platform_parse_stat_box: {
    'zh-CN': '解析属性面板',
    'en-US': 'Parse Stat Box',
  },
  platform_format_royalroad: {
    'zh-CN': '⚡ Royal Road 一键排版',
    'en-US': '⚡ Format for Royal Road',
  },
  platform_copy_code: {
    'zh-CN': '复制排版代码',
    'en-US': 'Copy Formatted Code',
  },
  platform_copied: {
    'zh-CN': '已复制！',
    'en-US': 'Copied!',
  },
  platform_load_sample: {
    'zh-CN': '载入样例',
    'en-US': 'Load Sample',
  },
  platform_load_err: {
    'zh-CN': '加载平台列表失败: {error}',
    'en-US': 'Failed to load platforms: {error}',
  },
  platform_target_label: {
    'zh-CN': '目标平台',
    'en-US': 'Target Platform',
  },
  platform_char_range_chip: {
    'zh-CN': '{min}-{max}字/章',
    'en-US': '{min}-{max} words/ch',
  },
  platform_climax_chip: {
    'zh-CN': '爽点周期: {interval}',
    'en-US': 'Payoff Pace: {interval}',
  },
  platform_chap_title_optional: {
    'zh-CN': '章节标题（可选）',
    'en-US': 'Chapter Title (Optional)',
  },
  platform_chap_text_label: {
    'zh-CN': '章节正文',
    'en-US': 'Chapter Text',
  },
  platform_suggest_chars: {
    'zh-CN': '建议 {min}-{max} 字',
    'en-US': 'Recommended {min}-{max} words',
  },
  platform_compliance_result: {
    'zh-CN': '合规检查结果',
    'en-US': 'Compliance Check Result',
  },
  platform_compliant_pass: {
    'zh-CN': '合规',
    'en-US': 'Compliant',
  },
  platform_compliant_fail: {
    'zh-CN': '不合规',
    'en-US': 'Non-compliant',
  },
  platform_char_count_suffix: {
    'zh-CN': '{count} 字',
    'en-US': '{count} words',
  },
  platform_diag_report_title: {
    'zh-CN': '签约过稿诊断报告',
    'en-US': 'Submission Readiness Report',
  },
  platform_diag_grade_chip: {
    'zh-CN': '评级 {grade} · 签约概率: {prob}',
    'en-US': 'Grade {grade} · Acceptance: {prob}',
  },
  platform_diag_score_chip: {
    'zh-CN': '签约潜力分: {score} / 100',
    'en-US': 'Potential Score: {score} / 100',
  },
  platform_diag_stats_summary: {
    'zh-CN': '字数: {count} | 对话占比: {ratio}%',
    'en-US': 'Words: {count} | Dialogue: {ratio}%',
  },
  platform_diag_veto_title: {
    'zh-CN': '致命劝退点（直接影响编辑初筛签约）:',
    'en-US': 'Fatal Dealbreakers (Affects editorial screening):',
  },
  platform_diag_fixes_title: {
    'zh-CN': '针对性修改建议:',
    'en-US': 'Actionable Suggestions:',
  },
  platform_diag_perfect_alert: {
    'zh-CN': '正文节奏与篇幅极佳，未发现明显编辑劝退项，保持当前水准即可投稿！',
    'en-US': 'Pacing and word count are optimal with no major editorial red flags. Ready for submission!',
  },
  platform_requirements_title: {
    'zh-CN': '平台要求',
    'en-US': 'Platform Requirements',
  },
  platform_mode_serial: {
    'zh-CN': '连载',
    'en-US': 'Serialized',
  },
  platform_mode_short: {
    'zh-CN': '短篇',
    'en-US': 'Short',
  },
  platform_req_summary: {
    'zh-CN': '{min}-{max}字 | {mode} | {genreCount} 题材',
    'en-US': '{min}-{max} words | {mode} | {genreCount} Genres',
  },
  platform_litrpg_workshop_title: {
    'zh-CN': 'LitRPG 属性面板与 Royal Road 格式化工坊',
    'en-US': 'LitRPG Stat Box & Royal Road Formatter',
  },
  platform_litrpg_workshop_desc: {
    'zh-CN': '智能提取 LitRPG / Progression Fantasy 的状态面板（Status Box），自动将其封装为符合 Royal Road 规范的 BBCode [spoiler] 折叠标签，并插入作者说头尾注释。' ,
    'en-US': 'Intelligently extracts LitRPG / Progression Fantasy Status Boxes, encapsulating them into Royal Road compliant BBCode [spoiler] tags with author notes.',
  },
  platform_litrpg_sample_btn: {
    'zh-CN': '填入海外爆款示例',
    'en-US': 'Load Bestseller Sample',
  },
  platform_litrpg_text_label: {
    'zh-CN': '章节正文（含属性面板）',
    'en-US': 'Chapter Draft (with Stat Boxes)',
  },
  platform_litrpg_text_ph: {
    'zh-CN': '在此输入包含属性面板的正文...',
    'en-US': 'Enter chapter text containing stat boxes...',
  },
  platform_rr_params_title: {
    'zh-CN': 'Royal Road 连载排版参数',
    'en-US': 'Royal Road Serialization Parameters',
  },
  platform_rr_note_head_label: {
    'zh-CN': "顶部作者说 (Author's Note Top)",
    'en-US': "Top Author's Note (Before Chapter)",
  },
  platform_rr_note_head_ph: {
    'zh-CN': '例如：Thanks for reading! Updates every Monday and Thursday.',
    'en-US': 'e.g. Thanks for reading! Updates every Monday and Thursday.',
  },
  platform_rr_note_foot_label: {
    'zh-CN': "底部作者说 / 呼吁投票 (Author's Note Bottom)",
    'en-US': "Bottom Author's Note / Call to Action",
  },
  platform_rr_note_foot_ph: {
    'zh-CN': "例如：Support the story on Patreon for advance chapters. Don't forget to rate!",
    'en-US': "e.g. Support the story on Patreon for advance chapters. Don't forget to rate!",
  },
  platform_rr_wrap_label: {
    'zh-CN': '自动将检测到的属性面板包裹为 [spoiler="..."] 折叠块（推荐：防止手机端大面积刷屏，极大改善读者留存）',
    'en-US': 'Wrap detected stat boxes into [spoiler="..."] tags (Recommended: prevents mobile text wall, improves retention)',
  },
  platform_statbox_result_title: {
    'zh-CN': '属性面板识别结果',
    'en-US': 'Stat Box Detection Results',
  },
  platform_statbox_count_chip: {
    'zh-CN': '共识别 {count} 个面板',
    'en-US': '{count} Stat Boxes Detected',
  },
  platform_statbox_empty_alert: {
    'zh-CN': '未在正文中检测到符合规范的属性面板。支持格式：[Status Window]、ASCII 边框框选、或 【属性面板】。',
    'en-US': 'No compliant stat boxes detected. Supported formats: [Status Window], ASCII borders, or 【Status Panel】.',
  },
  platform_statbox_type_label: {
    'zh-CN': '类型: {type}',
    'en-US': 'Type: {type}',
  },
  platform_statbox_pos_label: {
    'zh-CN': '位置: 第 {start} - {end} 字符 ({count} 字)',
    'en-US': 'Position: Chars {start} - {end} ({count} chars)',
  },
  platform_rr_bbcode_title: {
    'zh-CN': 'Royal Road BBCode 排版稿',
    'en-US': 'Royal Road BBCode Formatted Manuscript',
  },
  platform_rr_bbcode_badge: {
    'zh-CN': 'BBCode 格式',
    'en-US': 'BBCode Format',
  },
  platform_copied_alert: {
    'zh-CN': '排版文本已成功复制到剪贴板，可直接粘贴发布至 Royal Road 章节编辑器！',
    'en-US': 'Formatted text copied to clipboard. Ready to paste into Royal Road chapter editor!',
  },

  // 毒点排查与弃坑避雷
  poison_tab_scanner: {
    'zh-CN': '毒点快速排查 (本地规则)',
    'en-US': 'Anti-Poison Scanner (Local)',
  },
  poison_tab_library: {
    'zh-CN': '弃坑避雷规范库 (10大红线)',
    'en-US': 'Fatal Taboo Library (10 Rules)',
  },
  poison_desc: {
    'zh-CN': '基于商业网文大数据提炼的纯本地 10 大核心毒点检测器（过度憋屈、圣母资敌、降智舔狗、战力断崖、长篇说教、女配白送、绿帽擦边等）。不消耗大模型 Token，零网络延迟。',
    'en-US': 'Local rule-based scanner for 10 fatal novel taboos (excessive suffering, enemy mercy, simp behavior, power collapse, preachy monologue, etc.). Zero token cost, zero latency.',
  },
  poison_placeholder: {
    'zh-CN': '请在此粘贴需要检测的章节正文或剧情草稿...',
    'en-US': 'Paste chapter draft or plot outline to inspect for fatal taboos...',
  },
  poison_scan_action: {
    'zh-CN': '一键扫描毒点',
    'en-US': 'Scan for Taboos',
  },
  poison_clear: {
    'zh-CN': '清空',
    'en-US': 'Clear',
  },
  poison_result_title: {
    'zh-CN': '检测结果：',
    'en-US': 'Audit Result:',
  },
  poison_score_label: {
    'zh-CN': '毒点扣分值：',
    'en-US': 'Penalty Score:',
  },
  poison_issues_count: {
    'zh-CN': '检出问题：',
    'en-US': 'Issues Found:',
  },
  poison_score_unit: {
    'zh-CN': '分（0分最佳）',
    'en-US': 'pts (0 is cleanest)',
  },
  poison_issues_unit: {
    'zh-CN': '处',
    'en-US': 'found',
  },
  poison_clean_alert: {
    'zh-CN': '干得漂亮！本段正文未命中任何已知的恶性毒点或降智情节，行文节奏舒畅。',
    'en-US': 'Excellent! No major narrative taboos or fatal drop-off points detected.',
  },
  poison_findings_title: {
    'zh-CN': '检出问题清单与修改建议：',
    'en-US': 'Detected Issues & Revision Guide:',
  },
  poison_matched_prefix: {
    'zh-CN': '命中关键词：',
    'en-US': 'Trigger: ',
  },
  poison_reader_pain: {
    'zh-CN': '【读者痛点】',
    'en-US': '[Reader Dropoff]',
  },
  poison_fix_guide: {
    'zh-CN': '【修改建议】',
    'en-US': '[Actionable Fix]',
  },
  poison_library_desc: {
    'zh-CN': '数百万商业读者验证的 10 大弃坑毒点红线清单。下笔前对照自检，避免因为一处剧情瑕疵引发书评区差评暴动。',
    'en-US': '10 fatal taboo rules verified by millions of webnovel readers. Review before publishing to avoid mass reader dropoffs.',
  },
  poison_fatal_tag: {
    'zh-CN': '绝对红线',
    'en-US': 'Fatal Redline',
  },
  poison_high_tag: {
    'zh-CN': '高危警报',
    'en-US': 'High Warning',
  },
  poison_phenomenon: {
    'zh-CN': '现象描述：',
    'en-US': 'Description: ',
  },
  poison_reader_reaction: {
    'zh-CN': '读者反应：',
    'en-US': 'Reader Reaction: ',
  },
  poison_taboo_guide: {
    'zh-CN': '【避雷指南】',
    'en-US': '[Avoidance Guide]',
  },

  // 去 AI 味全维度诊断与润色 (DeslopPanel)
  deslop_title: {
    'zh-CN': '去 AI 味全维度诊断与润色',
    'en-US': 'Anti-Slop Full-Spectrum Diagnostics & Polish',
  },
  deslop_desc: {
    'zh-CN': '精准扫描假大空修辞、同义反复、直陈式情绪喊话、机械排比与「让」字被动句',
    'en-US': 'Precision scan for LLM clichés, tautologies, filter words, mechanical parallelism, and passive phrasing',
  },
  deslop_btn_compare: {
    'zh-CN': '一键生成去味稿并对比',
    'en-US': 'Generate Polished Draft & Compare',
  },
  deslop_placeholder: {
    'zh-CN': '在此粘贴待检测的章节或片段……（支持万字长文快速诊断）',
    'en-US': 'Paste chapter or snippet to diagnose... (supports quick scan of 10k+ words)',
  },
  deslop_char_count: {
    'zh-CN': '当前字数：',
    'en-US': 'Length: ',
  },
  deslop_chars_unit: {
    'zh-CN': '字',
    'en-US': 'chars',
  },
  deslop_mode_auto: {
    'zh-CN': '双语自适应',
    'en-US': 'Bilingual Auto',
  },
  deslop_mode_zh: {
    'zh-CN': '中文网文',
    'en-US': 'Chinese Webnovel',
  },
  deslop_mode_en: {
    'zh-CN': 'Exoscribe 英文',
    'en-US': 'Exoscribe English',
  },
  deslop_scanning: {
    'zh-CN': '全维扫描中…',
    'en-US': 'Scanning...',
  },
  deslop_btn_diagnose: {
    'zh-CN': '开始去 AI 味诊断',
    'en-US': 'Start Anti-Slop Diagnosis',
  },
  deslop_score_title: {
    'zh-CN': 'AI 味指数（越低越自然）',
    'en-US': 'Slop Index (lower is more natural)',
  },
  deslop_suggestions_title: {
    'zh-CN': '核心优化建议',
    'en-US': 'Key Suggestions',
  },
  deslop_clean_success: {
    'zh-CN': '✓ 文风非常自然生动，未检测到典型 AI 模板句式与机械套路！',
    'en-US': '✓ Prose is exceptionally natural and vivid, no typical AI clichés or mechanical tropes detected!',
  },
  deslop_word_count: {
    'zh-CN': '有效字数',
    'en-US': 'Word Count',
  },
  deslop_western_word_count: {
    'zh-CN': '西文词数',
    'en-US': 'Western Words',
  },
  deslop_sentence_count: {
    'zh-CN': '句子总数',
    'en-US': 'Sentences',
  },
  deslop_issues_found: {
    'zh-CN': '命中疑点',
    'en-US': 'Issues Found',
  },
  deslop_count_unit: {
    'zh-CN': '处',
    'en-US': 'found',
  },
  deslop_adverb_density: {
    'zh-CN': '-ly 副词占比',
    'en-US': '-ly Adverb Ratio',
  },
  deslop_rang_density: {
    'zh-CN': '「让」字千字密度',
    'en-US': 'Rang Passive Density',
  },
  deslop_issues_title: {
    'zh-CN': '问题定位与逐句优化清单',
    'en-US': 'Issue Locations & Sentence Optimization Checklist',
  },
  deslop_no_issues: {
    'zh-CN': '未发现需整改的 AI 模板句式',
    'en-US': 'No AI template phrasing requiring revision found',
  },
  deslop_optimize_tip: {
    'zh-CN': '💡 优化建议：',
    'en-US': '💡 Suggestion: ',
  },
  deslop_empty_input_error: {
    'zh-CN': '请输入需要诊断的章节文本',
    'en-US': 'Please enter chapter text to diagnose',
  },
  deslop_error_prefix: {
    'zh-CN': '诊断失败: ',
    'en-US': 'Diagnosis failed: ',
  },

  // 双栏对比审校视图 (DiffReviewView)
  diff_title: {
    'zh-CN': '双栏对比审校',
    'en-US': 'Side-by-Side Review',
  },
  diff_orig_prefix: {
    'zh-CN': '原稿',
    'en-US': 'Original',
  },
  diff_polish_prefix: {
    'zh-CN': '润色稿',
    'en-US': 'Polished',
  },
  diff_paras_unit: {
    'zh-CN': '段',
    'en-US': 'paras',
  },
  diff_copy_btn: {
    'zh-CN': '复制润色稿',
    'en-US': 'Copy Polished',
  },
  diff_copied: {
    'zh-CN': '已复制！',
    'en-US': 'Copied!',
  },
  diff_reject_btn: {
    'zh-CN': '放弃改动',
    'en-US': 'Discard',
  },
  diff_accept_btn: {
    'zh-CN': '采纳润色稿',
    'en-US': 'Accept Polish',
  },
  diff_orig_header: {
    'zh-CN': '原稿（修改前）',
    'en-US': 'Original Draft (Before)',
  },
  diff_polish_header: {
    'zh-CN': 'AI 润色 / 去味优化稿',
    'en-US': 'AI Polish / Anti-Slop Revision (After)',
  },
  diff_empty_para: {
    'zh-CN': '（段落留白）',
    'en-US': '(Blank paragraph)',
  },

  // 创作工作台顶栏与流水线 (WritingWorkbench)
  workbench_mode_studio: {
    'zh-CN': '沉浸创作室 (Studio)',
    'en-US': 'Writing Studio',
  },
  workbench_mode_pipeline: {
    'zh-CN': '工坊流水线 (Pipeline)',
    'en-US': 'Craft Pipeline',
  },
  pipeline_tab_inject: {
    'zh-CN': '资产注入',
    'en-US': 'Asset Injection',
  },
  pipeline_tab_generate: {
    'zh-CN': 'AI 章节生成',
    'en-US': 'Chapter Generation',
  },
  pipeline_tab_score: {
    'zh-CN': '单章质检打分',
    'en-US': 'Quality Scoring',
  },
  pipeline_tab_assemble: {
    'zh-CN': '拆书资产组装',
    'en-US': 'Deconstruction Matrix',
  },
  pipeline_tab_style: {
    'zh-CN': '文风模型分析',
    'en-US': 'Voice & Style Modeling',
  },
  pipeline_tab_extras: {
    'zh-CN': '创作者企划中心',
    'en-US': 'Creator Project Hub',
  },
  pipeline_tab_deslop: {
    'zh-CN': '去 AI 味实验室',
    'en-US': 'Anti-Slop Lab',
  },
  pipeline_tab_poison: {
    'zh-CN': '灵感与毒点避雷工坊',
    'en-US': 'Inspiration & Taboo Shield',
  },
  pipeline_tab_essence: {
    'zh-CN': '小说精华数据库',
    'en-US': 'Fiction Essence Vault',
  },
  // WS-A6：simple 模式下 9 tab 的三组分组标题
  pipeline_group_create: {
    'zh-CN': '创作',
    'en-US': 'Create',
  },
  pipeline_group_tools: {
    'zh-CN': '工具',
    'en-US': 'Tools',
  },
  pipeline_group_manage: {
    'zh-CN': '管理',
    'en-US': 'Manage',
  },
  // 帮助中心：三步闭环小节标题（数据源为 help/journeys.ts，与首页 JourneyStepper 同源）
  help_start_journey_title: {
    'zh-CN': '三步闭环（与首页进度条一致）',
    'en-US': 'The 3-Step Loop (same as the home progress bar)',
  },

  // 创作扩展企划中心 (WritingExtras)
  extras_project_label: {
    'zh-CN': '写作项目',
    'en-US': 'Project',
  },
  extras_project_desc: {
    'zh-CN': '大纲、人物、便签、创作者仪表盘与导出均按项目隔离',
    'en-US': 'Outlines, characters, notes, dashboard, and exports are scoped by project',
  },
  extras_no_project_alert: {
    'zh-CN': '请先在「写作」页签新建写作项目',
    'en-US': 'Please create a writing project in the Writing Studio first',
  },
  extras_tab_outline: {
    'zh-CN': '大纲架构',
    'en-US': 'Outline & Structure',
  },
  extras_tab_character: {
    'zh-CN': '人物卡与关系',
    'en-US': 'Characters & Relations',
  },
  extras_tab_notes: {
    'zh-CN': '灵感便签',
    'en-US': 'Inspiration Notes',
  },
  extras_tab_dashboard: {
    'zh-CN': '创作者仪表盘',
    'en-US': 'Creator Dashboard',
  },
  extras_tab_export: {
    'zh-CN': '规范导出',
    'en-US': 'Manuscript Export',
  },

  // 大纲架构面板 (OutlinePanel)
  extras_outline_volume: {
    'zh-CN': '卷',
    'en-US': 'Vol',
  },
  extras_outline_chapter: {
    'zh-CN': '章',
    'en-US': 'Ch',
  },
  extras_outline_status_planned: {
    'zh-CN': '待写',
    'en-US': 'Planned',
  },
  extras_outline_status_writing: {
    'zh-CN': '写作中',
    'en-US': 'Drafting',
  },
  extras_outline_status_done: {
    'zh-CN': '已完成',
    'en-US': 'Completed',
  },
  extras_outline_add_btn: {
    'zh-CN': '新增分卷 / 章节',
    'en-US': 'Add Volume / Chapter',
  },
  extras_outline_hook_template_btn: {
    'zh-CN': '🚀 引用黄金三章模板',
    'en-US': '🚀 First 3 Chapters Template',
  },
  extras_outline_empty: {
    'zh-CN': '还没有大纲，先从第一卷/第一章开始规划架构吧',
    'en-US': 'No outlines yet. Start planning from Volume 1 or Chapter 1',
  },
  extras_outline_edit_title: {
    'zh-CN': '编辑大纲',
    'en-US': 'Edit Outline',
  },
  extras_outline_new_title: {
    'zh-CN': '新增大纲架构',
    'en-US': 'New Outline Item',
  },
  extras_outline_kind: {
    'zh-CN': '类型',
    'en-US': 'Type',
  },
  extras_outline_kind_volume: {
    'zh-CN': '分卷（Volume）',
    'en-US': 'Volume',
  },
  extras_outline_kind_chapter: {
    'zh-CN': '章节（Chapter）',
    'en-US': 'Chapter',
  },
  extras_outline_item_title: {
    'zh-CN': '标题',
    'en-US': 'Title',
  },
  extras_outline_summary: {
    'zh-CN': '内容概要 / 剧情线',
    'en-US': 'Summary / Plotline',
  },
  extras_outline_summary_ph: {
    'zh-CN': '这一卷/章的核心冲突、情绪线、重要伏笔……',
    'en-US': 'Core conflict, emotional arc, key foreshadowing for this volume/chapter...',
  },
  extras_outline_status: {
    'zh-CN': '状态',
    'en-US': 'Status',
  },
  extras_outline_template_dialog_title: {
    'zh-CN': '🚀 黄金三章开篇模型库',
    'en-US': '🚀 First 3 Chapters Hook Models',
  },
  extras_outline_template_dialog_subtitle: {
    'zh-CN': '内置 10 大提升留存率的成熟开篇节拍',
    'en-US': 'Built-in 10 battle-tested beats to maximize reader retention',
  },
  extras_outline_template_select: {
    'zh-CN': '选择开篇模板',
    'en-US': 'Select Opening Template',
  },
  extras_outline_template_first300: {
    'zh-CN': '🔥 前 300 字吸睛钩子：',
    'en-US': '🔥 First 300 Words Hook:',
  },
  extras_outline_template_beat1: {
    'zh-CN': '第 1 章节拍（生死危机与冲突）：',
    'en-US': 'Chapter 1 Beat (Crisis & Immediate Conflict):',
  },
  extras_outline_template_beat2: {
    'zh-CN': '第 2 章节拍（压迫激化与转机）：',
    'en-US': 'Chapter 2 Beat (Escalation & Opportunity):',
  },
  extras_outline_template_beat3: {
    'zh-CN': '第 3 章节拍（首爽破局与爽点兑现）：',
    'en-US': 'Chapter 3 Beat (First Payoff & Breakthrough):',
  },
  extras_outline_template_apply: {
    'zh-CN': '一键应用为前三章大纲',
    'en-US': 'Apply as Chapters 1-3 Outline',
  },

  // 人物卡与关系网 (CharacterPanel)
  extras_char_add_btn: {
    'zh-CN': '新建人物卡',
    'en-US': 'New Character Card',
  },
  extras_char_empty: {
    'zh-CN': '还没有人物卡，先给主角建立第一张人设立体档案吧',
    'en-US': 'No characters yet. Create a dimensional profile for your protagonist',
  },
  extras_char_edit_title: {
    'zh-CN': '编辑人物卡档案',
    'en-US': 'Edit Character Profile',
  },
  extras_char_new_title: {
    'zh-CN': '新建人物卡档案',
    'en-US': 'New Character Profile',
  },
  extras_char_name: {
    'zh-CN': '姓名',
    'en-US': 'Name',
  },
  extras_char_random_name: {
    'zh-CN': '🎲 随机名',
    'en-US': '🎲 Random Name',
  },
  extras_char_role: {
    'zh-CN': '定位',
    'en-US': 'Role',
  },
  extras_char_role_ph: {
    'zh-CN': '如：男主 / 女主 / 幕后黑手 / 剑术师尊……',
    'en-US': 'e.g. Protagonist / Deuteragonist / Hidden Master / Antagonist...',
  },
  extras_char_camp: {
    'zh-CN': '所属阵营',
    'en-US': 'Faction / Alignment',
  },
  extras_char_camp_protagonist: {
    'zh-CN': '主角阵营',
    'en-US': 'Protagonist Faction',
  },
  extras_char_camp_antagonist: {
    'zh-CN': '反派宿敌',
    'en-US': 'Antagonist / Rival',
  },
  extras_char_camp_neutral: {
    'zh-CN': '中立势力',
    'en-US': 'Neutral Power',
  },
  extras_char_camp_sect: {
    'zh-CN': '宗门高层',
    'en-US': 'Sect Leadership',
  },
  extras_char_camp_hermit: {
    'zh-CN': '世外高人',
    'en-US': 'Hermit Sage',
  },
  extras_char_rel_target: {
    'zh-CN': '关系关联角色',
    'en-US': 'Related Character',
  },
  extras_char_rel_target_ph: {
    'zh-CN': '如：林天（留空则不设）',
    'en-US': 'e.g. Lin Tian (blank if none)',
  },
  extras_char_rel_type: {
    'zh-CN': '关系类型',
    'en-US': 'Relation Type',
  },
  extras_char_rel_type_ph: {
    'zh-CN': '如：宿敌 / 师徒 / 知己',
    'en-US': 'e.g. Rival / Master / Ally',
  },
  extras_char_desc: {
    'zh-CN': '性格特质、人设背景与人物弧光',
    'en-US': 'Personality, Backstory & Character Arc',
  },
  extras_char_desc_ph: {
    'zh-CN': '外貌特征、口癖、行为动机、阴暗面、核心羁绊……',
    'en-US': 'Appearance, catchphrases, core motivation, fatal flaw, relationships...',
  },

  // 灵感便签 (NotePanel)
  extras_note_add_btn: {
    'zh-CN': '速记灵感',
    'en-US': 'Quick Note',
  },
  extras_note_empty: {
    'zh-CN': '灵感稍纵即逝，随时把冒出的金句、桥段、反转记在这里',
    'en-US': 'Inspiration is fleeting. Record memorable lines, twists, and tropes here anytime',
  },
  extras_note_untitled: {
    'zh-CN': '（无标题灵感）',
    'en-US': '(Untitled Note)',
  },
  extras_note_edit_title: {
    'zh-CN': '编辑灵感便签',
    'en-US': 'Edit Note',
  },
  extras_note_new_title: {
    'zh-CN': '速记一条灵感',
    'en-US': 'New Inspiration Note',
  },
  extras_note_title: {
    'zh-CN': '标题',
    'en-US': 'Title',
  },
  extras_note_content: {
    'zh-CN': '灵感详情',
    'en-US': 'Content',
  },
  extras_note_content_ph: {
    'zh-CN': '突然想到的战斗机制、反转包袱、人物对白金句……',
    'en-US': 'Combat mechanics, reveal setups, punchlines, witty dialogue...',
  },

  // 创作者仪表盘 (DashboardPanel)
  extras_dash_title: {
    'zh-CN': '创作者数据大盘',
    'en-US': 'Creator Analytics Dashboard',
  },
  extras_dash_timespan: {
    'zh-CN': '时间跨度',
    'en-US': 'Time Range',
  },
  extras_dash_7days: {
    'zh-CN': '近 7 天',
    'en-US': 'Last 7 Days',
  },
  extras_dash_30days: {
    'zh-CN': '近 30 天',
    'en-US': 'Last 30 Days',
  },
  extras_dash_90days: {
    'zh-CN': '近 90 天',
    'en-US': 'Last 90 Days',
  },
  extras_dash_loading: {
    'zh-CN': '正在加载创作者大盘数据……',
    'en-US': 'Loading analytics data...',
  },
  extras_dash_today_words: {
    'zh-CN': '今日码字',
    'en-US': "Today's Words",
  },
  extras_dash_words_unit: {
    'zh-CN': '字',
    'en-US': 'words',
  },
  extras_dash_total_words: {
    'zh-CN': '全书总字数',
    'en-US': 'Total Book Words',
  },
  extras_dash_chapters_unit: {
    'zh-CN': '章已落盘',
    'en-US': 'chapters written',
  },
  extras_dash_streak: {
    'zh-CN': '连续更文',
    'en-US': 'Writing Streak',
  },
  extras_dash_streak_unit: {
    'zh-CN': '天不断更',
    'en-US': 'day streak',
  },
  extras_dash_today_chapters: {
    'zh-CN': '今日成章',
    'en-US': "Today's Chapters",
  },
  extras_dash_chapters_done: {
    'zh-CN': '章',
    'en-US': 'chapters',
  },
  extras_dash_creation_chart_title: {
    'zh-CN': '每日码字与创作速率平滑折线',
    'en-US': 'Daily Words & Writing Rate Trajectory',
  },
  extras_dash_wave_chart_title: {
    'zh-CN': '章节情绪张力起伏波形（起承转合）',
    'en-US': 'Narrative Tension & Pacing Waveform',
  },
  extras_dash_benchmark: {
    'zh-CN': '对标神作',
    'en-US': 'Benchmark',
  },
  extras_dash_bm_classic: {
    'zh-CN': '经典起承转合',
    'en-US': 'Classic 4-Act Pacing',
  },
  extras_dash_bm_fast_hook: {
    'zh-CN': '黄金强入局',
    'en-US': 'Golden In Medias Res',
  },
  extras_dash_bm_steady: {
    'zh-CN': '稳健发育流',
    'en-US': 'Steady Progression',
  },
  extras_dash_bm_face_slap: {
    'zh-CN': '压抑打脸流',
    'en-US': 'Tension & Reversal',
  },
  extras_dash_btn_analyze: {
    'zh-CN': '测算草稿',
    'en-US': 'Analyze Draft',
  },
  extras_dash_radar_title: {
    'zh-CN': '网文爽点节奏多维雷达图',
    'en-US': 'Narrative Rhythm & Payoff Radar',
  },
  extras_dash_radar_subtitle: {
    'zh-CN': '爽点推进、打脸期待、信息密度、金手指进化、章末钩子全维扫描',
    'en-US': 'Payoff velocity, anticipation, information density, power progression, end-of-chapter hooks',
  },

  // 规范多格式导出 (ExportPanel)
  extras_export_title: {
    'zh-CN': '导出全书作品',
    'en-US': 'Export Entire Book',
  },
  extras_export_desc: {
    'zh-CN': '纯 Python 标准库零依赖规范导出，支持直接交付排版、投稿或本地备份',
    'en-US': 'Zero-dependency pure standard library export for publishing, submission, or backup',
  },
  extras_export_docx_title: {
    'zh-CN': 'Word 规范文档 (.docx)',
    'en-US': 'Standard Word Document (.docx)',
  },
  extras_export_docx_tag: {
    'zh-CN': '国内出版 / 责编首选',
    'en-US': 'Industry Standard Submission',
  },
  extras_export_docx_desc: {
    'zh-CN': '符合网文投稿与出版规约，标题居中、章节居左、正文首行缩进 2 字符、1.5 倍行距，Word / WPS 秒开。',
    'en-US': 'Standard formatting: centered title, left-aligned chapters, indented paragraphs, 1.5 line spacing. Compatible with Word/WPS.',
  },
  extras_export_docx_btn: {
    'zh-CN': '导出 Word (.docx)',
    'en-US': 'Export Word (.docx)',
  },
  extras_export_epub_title: {
    'zh-CN': '标准电子书 (.epub)',
    'en-US': 'Standard eBook (.epub)',
  },
  extras_export_epub_tag: {
    'zh-CN': 'Kindle / Apple Books',
    'en-US': 'Kindle / Apple Books',
  },
  extras_export_epub_desc: {
    'zh-CN': 'EPUB 3.0 出版规范容器，无压缩 mimetype 居首，内嵌完整目录导航与样式，适配主流电子阅读器。',
    'en-US': 'EPUB 3.0 container with uncompressed mimetype, embedded navigation index, and responsive styling for e-readers.',
  },
  extras_export_epub_btn: {
    'zh-CN': '导出 EPUB (.epub)',
    'en-US': 'Export EPUB (.epub)',
  },
  extras_export_shunn_title: {
    'zh-CN': '国际标准文稿 (.txt)',
    'en-US': 'International Standard Manuscript (.txt)',
  },
  extras_export_shunn_tag: {
    'zh-CN': 'William Shunn SMF 规约',
    'en-US': 'William Shunn SMF Format',
  },
  extras_export_shunn_desc: {
    'zh-CN': '国际奇幻与科幻期刊通用投稿规范：页眉联系人、百字取整字数估算、居中标题与 # 场景分界符。',
    'en-US': 'Standard Manuscript Format (SMF) for English speculative fiction: contact block, word count rounding, centered header, # breaks.',
  },
  extras_export_shunn_btn: {
    'zh-CN': '导出 Shunn 文稿',
    'en-US': 'Export Shunn Manuscript',
  },
  extras_export_md_title: {
    'zh-CN': 'Markdown 结构化 (.md)',
    'en-US': 'Structured Markdown (.md)',
  },
  extras_export_md_tag: {
    'zh-CN': '跨平台排版首选',
    'en-US': 'Cross-platform Markdown',
  },
  extras_export_md_desc: {
    'zh-CN': '规范二级标题与元数据，适合导入 Obsidian、Typora、Notion 或多平台分发工具。',
    'en-US': 'Clean headings and metadata, ideal for Obsidian, Typora, Notion, or multi-platform distribution.',
  },
  extras_export_md_btn: {
    'zh-CN': '导出 Markdown (.md)',
    'en-US': 'Export Markdown (.md)',
  },
  extras_export_txt_title: {
    'zh-CN': '纯文本格式 (.txt)',
    'en-US': 'Plain Text Format (.txt)',
  },
  extras_export_txt_tag: {
    'zh-CN': '通用无格式备份',
    'en-US': 'Universal Plain Text',
  },
  extras_export_txt_desc: {
    'zh-CN': 'UTF-8 标准编码，按章号纯净拼接，各大网文作家后台直接全选粘贴无格式污染。',
    'en-US': 'UTF-8 standard encoding, clean chapter stitching without formatting artifacts. Direct paste ready.',
  },
  extras_export_txt_btn: {
    'zh-CN': '导出纯文本 (.txt)',
    'en-US': 'Export Plain Text (.txt)',
  },
  extras_tension_dialog_title: {
    'zh-CN': '测算章节情绪张力波形',
    'en-US': 'Calculate Chapter Tension Wave',
  },
  extras_tension_dialog_desc: {
    'zh-CN': '粘贴当前正在创作的章节草稿，系统将通过冲突关键词、标点短句节奏、人物对峙与感官微表情，计算整章情绪起伏波形并与标杆对齐。',
    'en-US': 'Paste draft text to compute sentence-level tension curves via conflict keywords, pacing rhythm, and character micro-expressions aligned with benchmark masterpieces.',
  },
  extras_tension_draft_label: {
    'zh-CN': '章节正文草稿',
    'en-US': 'Chapter Draft Content',
  },
  extras_tension_draft_ph: {
    'zh-CN': '粘贴本章草稿内容……（建议 1,000 字以上以获得更精准波形）',
    'en-US': 'Paste chapter draft here... (1,000+ words recommended for optimal waveform resolution)',
  },
  extras_tension_sample_btn: {
    'zh-CN': '填入示范高潮草稿',
    'en-US': 'Load Sample Climax Draft',
  },
  extras_tension_analyzing: {
    'zh-CN': '分析中…',
    'en-US': 'Analyzing...',
  },
  extras_tension_start_btn: {
    'zh-CN': '开始比对',
    'en-US': 'Start Comparison',
  },
  extras_golden_three_btn: {
    'zh-CN': '黄金三章连环比对',
    'en-US': 'Golden 3 Chapters Comparison',
  },
  extras_golden_three_dialog_title: {
    'zh-CN': '黄金三章张力曲线重叠比对',
    'en-US': 'Golden Three Chapters Tension Comparator',
  },
  extras_golden_three_dialog_desc: {
    'zh-CN': '连环测算网络小说前三章张力波形，与商业神作标杆对齐，精准检测中段失速、首章吸睛度与章末断章悬念。',
    'en-US': 'Analyze the first three chapters tension waveforms against commercial masterpiece benchmarks, detecting middle stalling, opening hooks, and cliffhangers.',
  },
  extras_golden_three_ch1: {
    'zh-CN': '第一章：开篇危机与入局',
    'en-US': 'Chapter 1: Opening Crisis & Hook',
  },
  extras_golden_three_ch2: {
    'zh-CN': '第二章：承接升级防失速',
    'en-US': 'Chapter 2: Escalation & Retention',
  },
  extras_golden_three_ch3: {
    'zh-CN': '第三章：首轮高潮与断章',
    'en-US': 'Chapter 3: First Climax & Cliffhanger',
  },
  extras_golden_three_sample_btn: {
    'zh-CN': '载入示范三章范例',
    'en-US': 'Load Sample 3 Chapters',
  },
  extras_golden_three_start_btn: {
    'zh-CN': '开始三章联合比对',
    'en-US': 'Start 3-Chapter Comparison',
  },
  extras_golden_three_handoff_title: {
    'zh-CN': '跨章过渡动量诊断',
    'en-US': 'Chapter Handoff Momentum',
  },
  extras_retention_btn: {
    'zh-CN': '读者留存预测',
    'en-US': 'Reader Retention Predictor',
  },
  extras_retention_dialog_title: {
    'zh-CN': '商业网文读者留存流失预测模型',
    'en-US': 'Commercial Reader Churn & Retention Estimator',
  },
  extras_retention_dialog_desc: {
    'zh-CN': '基于前三章细粒度情绪张力、首章入局刺激、平淡注水期漏斗、跨章过渡断崖与末尾留钩，量化推导各章节读者留存衰减曲线并精准定位跳出高危点。',
    'en-US': 'Simulate chapter-by-chapter reader retention decay curves based on tension, opening stimulation, pacing funnels, handoff cliff drops, and cliffhangers.',
  },
  extras_retention_sample_high: {
    'zh-CN': '载入示范高留存三章 (S/A级)',
    'en-US': 'Load Sample High Retention (S/A)',
  },
  extras_retention_sample_drop: {
    'zh-CN': '载入示范断崖失速三章 (高危跳出)',
    'en-US': 'Load Sample Cliff Drop (High Risk)',
  },
  extras_retention_start_btn: {
    'zh-CN': '开始读者留存测算',
    'en-US': 'Estimate Reader Retention',
  },
  extras_retention_result_title: {
    'zh-CN': '商业成色与读者留存全景',
    'en-US': 'Reader Retention & Commercial Grade',
  },
  extras_retention_final_rate: {
    'zh-CN': '终局预计留存率',
    'en-US': 'Projected Final Retention',
  },
  extras_retention_total_churn: {
    'zh-CN': '累计流失漏斗',
    'en-US': 'Total Churn Funnel',
  },
  extras_retention_hotspots_title: {
    'zh-CN': '弃读跳出高危风险点与挽留改法',
    'en-US': 'Drop-off Hotspots & Retention Fixes',
  },
  extras_retention_advice_title: {
    'zh-CN': '战略防跳出与留存优化建议',
    'en-US': 'Strategic Retention Recommendations',
  },
  extras_export_success: {
    'zh-CN': '成功导出 {chapters} 章、约 {words} 字：{filename}',
    'en-US': 'Successfully exported {chapters} chapters, ~{words} words: {filename}',
  },
  extras_export_error: {
    'zh-CN': '导出失败: {error}',
    'en-US': 'Export failed: {error}',
  },
  extras_exporting_docx: {
    'zh-CN': '生成 docx 中…',
    'en-US': 'Generating docx...',
  },
  extras_exporting_epub: {
    'zh-CN': '打包 epub 中…',
    'en-US': 'Packaging epub...',
  },
  extras_exporting_shunn: {
    'zh-CN': '生成文稿中…',
    'en-US': 'Formatting manuscript...',
  },
  extras_exporting_md: {
    'zh-CN': '生成 md 中…',
    'en-US': 'Generating md...',
  },
  extras_exporting_txt: {
    'zh-CN': '拼接 txt 中…',
    'en-US': 'Concatenating txt...',
  },

  extras_dash_wave_subtitle: {
    'zh-CN': '监测剧情平淡期与高潮爆发期，红线为章节实测，虚线为神作对标基准',
    'en-US': 'Detects flat pacing vs climax bursts — solid line is your chapter, dashed line is the benchmark',
  },
  extras_golden_three_combined_fit: {
    'zh-CN': '综合拟合度: {score}%',
    'en-US': 'Combined Fit: {score}%',
  },
  extras_golden_three_cliff_rating: {
    'zh-CN': '断章评级: {rating}',
    'en-US': 'Cliffhanger: {rating}',
  },
  extras_golden_three_handoff_chip: {
    'zh-CN': '第{from}章→第{to}章: {status} (落差{drop}分)',
    'en-US': 'Ch.{from}→Ch.{to}: {status} (drop {drop})',
  },
  extras_golden_three_status_cliff: {
    'zh-CN': '⚠️断崖失速',
    'en-US': '⚠️Cliff Drop',
  },
  extras_golden_three_status_smooth: {
    'zh-CN': '✅平滑承接',
    'en-US': '✅Smooth Handoff',
  },
  extras_golden_three_expert_advice: {
    'zh-CN': '黄金三章专家修改建议：',
    'en-US': 'Golden 3 Expert Suggestions:',
  },
  extras_golden_three_back_single: {
    'zh-CN': '返回单章',
    'en-US': 'Back to Single',
  },
  extras_tension_bm_fit: {
    'zh-CN': '标杆拟合度: {score}%',
    'en-US': 'Benchmark Fit: {score}%',
  },
  extras_tension_climax: {
    'zh-CN': '最高潮: {seg} ({score}分)',
    'en-US': 'Climax: {seg} ({score})',
  },
  extras_tension_avg_var: {
    'zh-CN': '均值: {avg} ｜ 波动: ±{variance}',
    'en-US': 'Avg: {avg} | Variance: ±{variance}',
  },
  extras_outline_move_up_aria: {
    'zh-CN': '上移',
    'en-US': 'Move up',
  },
  extras_outline_move_down_aria: {
    'zh-CN': '下移',
    'en-US': 'Move down',
  },
  extras_action_edit_aria: {
    'zh-CN': '编辑',
    'en-US': 'Edit',
  },
  extras_action_delete_aria: {
    'zh-CN': '删除',
    'en-US': 'Delete',
  },

  // 黄金三章对话框 - 标杆标签（复用于 Golden Three + Retention 弹窗）
  extras_benchmark_label: {
    'zh-CN': '商业神作标杆类型',
    'en-US': 'Benchmark Template',
  },
  extras_benchmark_classic: {
    'zh-CN': '经典商业递进三章标杆',
    'en-US': 'Classic Commercial Progression',
  },
  extras_benchmark_upgrade: {
    'zh-CN': '升级爽文逆袭打脸标杆',
    'en-US': 'Power-Up Revenge Arc',
  },
  extras_benchmark_fast_hook: {
    'zh-CN': '快穿生死时速高压标杆',
    'en-US': 'High-Stakes Fast Hook',
  },
  extras_benchmark_suspense: {
    'zh-CN': '悬疑无限流惊悚标杆',
    'en-US': 'Infinite Suspense / Thriller',
  },
  extras_golden_three_ch1_ph: {
    'zh-CN': '粘贴第 1 章正文草稿（前 30% 快速入局，章末留下微悬念钩子）……',
    'en-US': 'Paste Chapter 1 draft (hook in first 30%, end with a micro-cliffhanger)...',
  },
  extras_golden_three_ch2_ph: {
    'zh-CN': '粘贴第 2 章正文草稿（防中段失速塌陷，金手指与核心危机介入展开）……',
    'en-US': 'Paste Chapter 2 draft (avoid mid-arc sag, introduce power-up and core conflict)...',
  },
  extras_golden_three_ch3_ph: {
    'zh-CN': '粘贴第 3 章正文草稿（首卷爆发高潮与爽点释放，末尾强断章钩子）……',
    'en-US': 'Paste Chapter 3 draft (first-volume climax and payoff, end with a strong hook)...',
  },

  // 创作室与写作弹窗 (Writing Studio & Dialogs)
  writing_new_project_title: {
    'zh-CN': '新建写作项目',
    'en-US': 'Create Writing Project',
  },
  writing_project_name_label: {
    'zh-CN': '项目名',
    'en-US': 'Project Name',
  },
  writing_project_name_helper: {
    'zh-CN': '会作为目录名使用：不能包含 / \\，不能叫 default',
    'en-US': 'Used as directory name: cannot contain / \\, cannot be default',
  },
  studio_btn_meta: {
    'zh-CN': '企划定位',
    'en-US': 'Project Plan',
  },
  studio_btn_export: {
    'zh-CN': '全书导出',
    'en-US': 'Full Book Export',
  },
  studio_btn_pipeline: {
    'zh-CN': '工坊流水线',
    'en-US': 'Craft Pipeline',
  },
  studio_btn_next_ch: {
    'zh-CN': '下一章',
    'en-US': 'Next Chapter',
  },
  studio_today_written: {
    'zh-CN': '今日已写: {words} 字',
    'en-US': "Today's Words: {words}",
  },
  studio_creation_progress: {
    'zh-CN': '创作进度: {current} / {target} 字',
    'en-US': 'Progress: {current} / {target} words',
  },
  studio_collapse_copilot: {
    'zh-CN': '折叠右侧智能副驾',
    'en-US': 'Collapse AI Copilot',
  },
  studio_expand_copilot: {
    'zh-CN': '展开右侧智能副驾',
    'en-US': 'Expand AI Copilot',
  },
  studio_meta_dialog_title: {
    'zh-CN': '作品企划与多平台定位',
    'en-US': 'Project Planning & Platform Strategy',
  },
  studio_meta_platform_label: {
    'zh-CN': '目标签约平台',
    'en-US': 'Target Platform',
  },
  platform_fanqie_desc: {
    'zh-CN': '番茄小说 (30秒黄金钩/每章留扣/防虐主)',
    'en-US': 'Fanqie Novel (30s hook / cliffhangers / anti-frustration)',
  },
  platform_qidian_desc: {
    'zh-CN': '起点中文网 (大纵深世界观/严密升级/反圣母)',
    'en-US': 'Qidian (Deep worldbuilding / rigorous leveling / anti-bleeding-heart)',
  },
  platform_jinjiang_desc: {
    'zh-CN': '晋江文学城 (人设细腻反差/推拉克制/微表情)',
    'en-US': 'Jinjiang (Subtle character contrasts / restrained tension / micro-expressions)',
  },
  platform_qimao_desc: {
    'zh-CN': '七猫中文网 (开局强冲突受辱/底牌强反制)',
    'en-US': 'Qimao (High-conflict humiliation opening / decisive counterstrike)',
  },
  platform_zhihu_desc: {
    'zh-CN': '知乎盐选 (第一人称高反转/三幕式快节奏)',
    'en-US': 'Zhihu Salt (1st person twists / 3-act fast pacing)',
  },
  platform_general_desc: {
    'zh-CN': '通用网文平台',
    'en-US': 'General Fiction Platform',
  },
  studio_meta_genre_label: {
    'zh-CN': '小说题材',
    'en-US': 'Genre',
  },
  studio_meta_genre_ph: {
    'zh-CN': '例如：xianxia / dushi / xuanhuan',
    'en-US': 'e.g. xianxia / litrpg / fantasy',
  },
  studio_meta_target_words_label: {
    'zh-CN': '全书目标字数',
    'en-US': 'Target Word Count',
  },
  studio_meta_summary_label: {
    'zh-CN': '作品一句话卖点与核心主线',
    'en-US': 'Logline & Main Plot Objective',
  },
  studio_meta_summary_ph: {
    'zh-CN': '说明主角核心爽点、金手指与主线目标',
    'en-US': 'Core payoff hook, power mechanic, and endgame goal',
  },
  studio_meta_save_btn: {
    'zh-CN': '保存企划',
    'en-US': 'Save Project Plan',
  },
  studio_new_proj_title: {
    'zh-CN': '新建小说作品',
    'en-US': 'Create New Novel',
  },
  studio_new_proj_name_label: {
    'zh-CN': '小说作品名称',
    'en-US': 'Novel Title',
  },
  studio_new_proj_name_ph: {
    'zh-CN': '例如：万界仙途',
    'en-US': 'e.g. The Astral Path',
  },
  studio_export_dialog_title: {
    'zh-CN': '全书一键导出与排版生成',
    'en-US': 'Full Novel One-Click Export & Formatting',
  },
  studio_export_summary: {
    'zh-CN': '当前工程《{project}》已写 {chapters} 章，共 {words} 字。',
    'en-US': 'Current project "{project}" contains {chapters} chapters, ~{words} words.',
  },
  studio_export_format_label: {
    'zh-CN': '导出排版格式',
    'en-US': 'Export Format',
  },
  studio_export_format_docx: {
    'zh-CN': '📘 Word 文档 (.docx) — 官方标准排版稿（带标题封面）',
    'en-US': '📘 Word Document (.docx) — Official standard manuscript with title cover',
  },
  studio_export_format_epub: {
    'zh-CN': '📱 标准电子书 (.epub) — EPUB 3.0 出版容器（Kindle / Apple Books）',
    'en-US': '📱 Standard E-Book (.epub) — EPUB 3.0 publication container (Kindle / Apple Books)',
  },
  studio_export_format_shunn: {
    'zh-CN': '📑 国际投稿文稿 (.txt) — William Shunn 标准文稿格式（带字数估算）',
    'en-US': '📑 Standard Submission (.txt) — William Shunn manuscript format with word estimate',
  },
  studio_export_format_md: {
    'zh-CN': '📝 Markdown 结构稿 (.md) — 适合 Obsidian/知识库',
    'en-US': '📝 Markdown (.md) — Structured format for Obsidian / PKM',
  },
  studio_export_format_txt: {
    'zh-CN': '📄 纯文本 (.txt) — 干净无格式，直接复制粘贴',
    'en-US': '📄 Plain Text (.txt) — Clean unformatted text for quick copy-paste',
  },
  studio_exporting: {
    'zh-CN': '导出中...',
    'en-US': 'Exporting...',
  },
  studio_export_download_btn: {
    'zh-CN': '立即下载',
    'en-US': 'Download Now',
  },
  studio_new_outline_title: {
    'zh-CN': '规划新章节大纲',
    'en-US': 'Plan New Chapter Outline',
  },
  studio_outline_title_label: {
    'zh-CN': '章节标题',
    'en-US': 'Chapter Title',
  },
  studio_outline_title_ph: {
    'zh-CN': '例如：第2章 惊变',
    'en-US': 'e.g. Chapter 2 The Turning Point',
  },
  studio_outline_summary_label: {
    'zh-CN': '本章剧情细纲与冲突目标',
    'en-US': 'Chapter Plot Beats & Conflict Goals',
  },
  studio_outline_summary_ph: {
    'zh-CN': '说明本章主要发生什么事件、制造什么悬念或爽点',
    'en-US': 'Describe primary events, cliffhanger, or payoff hook',
  },
  studio_outline_save_btn: {
    'zh-CN': '保存大纲',
    'en-US': 'Save Outline',
  },
  studio_new_char_title: {
    'zh-CN': '新建核心人物设定卡',
    'en-US': 'Create Character Persona Card',
  },
  studio_char_name_label: {
    'zh-CN': '人物姓名',
    'en-US': 'Character Name',
  },
  studio_char_name_ph: {
    'zh-CN': '例如：白灵儿',
    'en-US': 'e.g. Bai Linger',
  },
  studio_char_role_label: {
    'zh-CN': '角色定位',
    'en-US': 'Character Archetype',
  },
  studio_char_role_protagonist: {
    'zh-CN': '主角 (主角光环/核心行动驱动)',
    'en-US': 'Protagonist (Core Agency / Driving Force)',
  },
  studio_char_role_heroine: {
    'zh-CN': '女主角 (羁绊/情感推拉)',
    'en-US': 'Heroine (Emotional Bond / Dynamic Tension)',
  },
  studio_char_role_villain: {
    'zh-CN': '反派 (压迫感/利益冲突)',
    'en-US': 'Antagonist (Pressure / Core Conflict)',
  },
  studio_char_role_rival: {
    'zh-CN': '宿敌 (镜像对照/势均力敌)',
    'en-US': 'Rival (Mirror Contrast / Worthy Adversary)',
  },
  studio_char_role_mentor: {
    'zh-CN': '导师 (传道/暗藏秘密)',
    'en-US': 'Mentor (Guidance / Hidden Secrets)',
  },
  studio_char_role_supporting: {
    'zh-CN': '配角 (插科打诨/辅助推进)',
    'en-US': 'Supporting (Comic Relief / Narrative Propellant)',
  },
  studio_char_desc_label: {
    'zh-CN': '人设反差与核心特质',
    'en-US': 'Character Contrast & Core Traits',
  },
  studio_char_desc_ph: {
    'zh-CN': '例如：表面清冷孤傲，实则内藏反差护短；具有关键血脉',
    'en-US': 'e.g. Outwardly aloof, fiercely protective inside; hidden lineage',
  },
  studio_char_save_btn: {
    'zh-CN': '保存人物',
    'en-US': 'Save Character',
  },
  studio_new_note_title: {
    'zh-CN': '随手记下灵感便签',
    'en-US': 'Capture Quick Idea Note',
  },
  studio_note_title_label: {
    'zh-CN': '便签标题',
    'en-US': 'Note Title',
  },
  studio_note_title_ph: {
    'zh-CN': '例如：万剑归宗的视觉描写',
    'en-US': 'e.g. Visual description of blade storm',
  },
  studio_note_content_label: {
    'zh-CN': '灵感详情',
    'en-US': 'Note Details',
  },
  studio_note_content_ph: {
    'zh-CN': '例如：剑气如雨倒卷长空，带出金石裂帛之音',
    'en-US': 'e.g. Swirling sword aura tearing through the sky with metallic resonance',
  },
  studio_note_save_btn: {
    'zh-CN': '保存便签',
    'en-US': 'Save Note',
  },
  studio_new_chain_title: {
    'zh-CN': '记录全书草蛇灰线（伏笔暗线）',
    'en-US': 'Record Foreshadowing Clue & Arc',
  },
  studio_chain_title_label: {
    'zh-CN': '伏笔线索名称',
    'en-US': 'Clue / Arc Name',
  },
  studio_chain_title_ph: {
    'zh-CN': '例如：林凡胸前神秘石珠的来历',
    'en-US': 'e.g. Origin of the mysterious stone pendant',
  },
  studio_chain_type_label: {
    'zh-CN': '伏笔类型',
    'en-US': 'Clue Category',
  },
  studio_chain_type_identity: {
    'zh-CN': '身份谜题 (主角或大反派隐匿身世)',
    'en-US': 'Identity Mystery (Hidden lineage of protagonist or antagonist)',
  },
  studio_chain_type_power: {
    'zh-CN': '力量伏笔 (神功残卷/异宝异动/底牌法则)',
    'en-US': 'Power Foreshadowing (Fragmented technique / relic awakening)',
  },
  studio_chain_type_fate: {
    'zh-CN': '恩怨宿命 (宗门灭顶旧案/复仇契机)',
    'en-US': 'Karmic Nemesis (Fallen sect conspiracy / vendetta)',
  },
  studio_chain_type_truth: {
    'zh-CN': '世界真相 (天地禁制/天道伪善/世界黑幕)',
    'en-US': 'World Truth (Cosmic restriction / divine hypocrisy / conspiracy)',
  },
  studio_chain_type_emotion: {
    'zh-CN': '情感暗涌 (红颜身份/背叛契机)',
    'en-US': 'Emotional Undercurrent (Hidden identity / betrayal trigger)',
  },
  studio_chain_plant_label: {
    'zh-CN': '埋设章号 (Plant)',
    'en-US': 'Plant Chapter',
  },
  studio_chain_reveal_label: {
    'zh-CN': '显露章号 (Reveal)',
    'en-US': 'Reveal Chapter',
  },
  studio_chain_climax_label: {
    'zh-CN': '回收章号 (Climax)',
    'en-US': 'Payoff / Climax Chapter',
  },
  studio_chain_desc_label: {
    'zh-CN': '暗线闭环规划与关键意象',
    'en-US': 'Clue Resolution Plan & Key Imagery',
  },
  studio_chain_desc_ph: {
    'zh-CN': '说明在埋设时给读者留下的微弱疑点，以及高潮时如何反转引爆',
    'en-US': 'Describe the subtle reader hook at plant and the explosive twist at payoff',
  },
  studio_chain_start_btn: {
    'zh-CN': '启动暗线追踪',
    'en-US': 'Start Clue Tracking',
  },

  // 灵感工坊 (InspirationWorkbench) - 8大标签页与各子模块
  inspiration_tab_name: {
    'zh-CN': '起名工坊 (离线智能)',
    'en-US': 'Smart Name Generator (Offline AI)',
  },
  inspiration_tab_hook: {
    'zh-CN': '开篇钩子库 (黄金三章)',
    'en-US': 'Opening Hooks (First 3 Chapters)',
  },
  inspiration_tab_goldfinger: {
    'zh-CN': '金手指机制库 (12大外挂)',
    'en-US': 'Power & Cheat Mechanics (12 Archetypes)',
  },
  inspiration_tab_shuangdian: {
    'zh-CN': '爽点打脸设计 (三段闭环)',
    'en-US': 'Trope & Climax Catharsis (3-Stage Loop)',
  },
  inspiration_tab_world: {
    'zh-CN': '世界观体系 (力量阶梯)',
    'en-US': 'Worldbuilding Systems (Power Ladder)',
  },
  inspiration_tab_dialogue: {
    'zh-CN': '名场面台词库 (反AI对话)',
    'en-US': 'Signature Dialogue & Anti-Slop (Spoken)',
  },
  inspiration_tab_character: {
    'zh-CN': '爆款人设矩阵 (反差弧光)',
    'en-US': 'Character Persona & Contrast Matrix',
  },
  inspiration_tab_emotion: {
    'zh-CN': '情绪高潮演出 (五感通感)',
    'en-US': 'Emotional Climax & Sensory Show-Don\'t-Tell',
  },

  // 1. 起名工坊
  inspiration_name_desc: {
    'zh-CN': '纯本地离线起名算法：自动结合古典意象与现代网感，规避烂大街套路名（如林动、萧炎式流水线），点击药丸直接复制到剪贴板。',
    'en-US': 'Pure local offline naming algorithm: fuses classical imagery and modern web feel, avoids generic cliché names. Click any chip to copy directly to clipboard.',
  },
  inspiration_name_kind_label: {
    'zh-CN': '生成类别',
    'en-US': 'Category',
  },
  inspiration_name_kind_character: {
    'zh-CN': '人物角色',
    'en-US': 'Character',
  },
  inspiration_name_kind_title: {
    'zh-CN': '爆款书名 (网文标题)',
    'en-US': 'Catchy Book Title',
  },
  inspiration_name_kind_sect: {
    'zh-CN': '宗门 / 仙门',
    'en-US': 'Sect / Clan',
  },
  inspiration_name_kind_corp: {
    'zh-CN': '集团 / 财阀',
    'en-US': 'Corporation / Conglomerate',
  },
  inspiration_name_kind_team: {
    'zh-CN': '电竞 / 战队',
    'en-US': 'Esports Team',
  },
  inspiration_name_kind_shelter: {
    'zh-CN': '末世 / 避难所',
    'en-US': 'Apocalyptic Shelter',
  },
  inspiration_name_kind_org: {
    'zh-CN': '怪谈 / 收容机构',
    'en-US': 'SCP / Anomaly Agency',
  },
  inspiration_name_kind_skill: {
    'zh-CN': '功法 / 战技',
    'en-US': 'Cultivation Art / Martial Skill',
  },
  inspiration_name_kind_artifact: {
    'zh-CN': '神兵 / 法宝',
    'en-US': 'Artifact / Divine Relic',
  },
  inspiration_name_novel_genre: {
    'zh-CN': '小说题材',
    'en-US': 'Novel Genre',
  },
  inspiration_genre_xianxia: {
    'zh-CN': '仙侠修真',
    'en-US': 'Xianxia / Cultivation',
  },
  inspiration_genre_dushi: {
    'zh-CN': '都市神豪',
    'en-US': 'Urban / Tycoon',
  },
  inspiration_genre_kehuan: {
    'zh-CN': '科幻末日',
    'en-US': 'Sci-Fi / Apocalypse',
  },
  inspiration_genre_xuanyi: {
    'zh-CN': '悬疑怪谈',
    'en-US': 'Suspense / Mystery',
  },
  inspiration_genre_duanpian: {
    'zh-CN': '知乎反转短篇',
    'en-US': 'Twist Short Story',
  },
  inspiration_name_style_label: {
    'zh-CN': '题材风格',
    'en-US': 'Theme Style',
  },
  inspiration_style_xianxia: {
    'zh-CN': '仙侠古典',
    'en-US': 'Classical Xianxia',
  },
  inspiration_style_dushi: {
    'zh-CN': '都市现代',
    'en-US': 'Modern Urban',
  },
  inspiration_style_kehuan: {
    'zh-CN': '科幻末世',
    'en-US': 'Sci-Fi Apocalypse',
  },
  inspiration_style_lishi: {
    'zh-CN': '历史争霸',
    'en-US': 'Historical Hegemony',
  },
  inspiration_style_wuxia: {
    'zh-CN': '传统武侠',
    'en-US': 'Traditional Wuxia',
  },
  inspiration_name_gender_label: {
    'zh-CN': '角色性别',
    'en-US': 'Gender',
  },
  inspiration_gender_all: {
    'zh-CN': '通用 / 随机',
    'en-US': 'Unisex / Random',
  },
  inspiration_gender_male: {
    'zh-CN': '男性',
    'en-US': 'Male',
  },
  inspiration_gender_female: {
    'zh-CN': '女性',
    'en-US': 'Female',
  },
  inspiration_gender_neutral: {
    'zh-CN': '中性 / 出尘',
    'en-US': 'Neutral / Ethereal',
  },
  inspiration_name_count_label: {
    'zh-CN': '生成数量',
    'en-US': 'Count',
  },
  inspiration_count_items: {
    'zh-CN': '个',
    'en-US': 'items',
  },
  inspiration_name_btn_generate: {
    'zh-CN': '换一批 (离线随机)',
    'en-US': 'Reroll (Offline Random)',
  },
  inspiration_name_empty: {
    'zh-CN': '暂无生成结果，请点击「换一批」生成。',
    'en-US': 'No generation results yet. Click "Reroll" to generate.',
  },
  inspiration_chip_tooltip: {
    'zh-CN': '点击复制到剪贴板',
    'en-US': 'Click to copy to clipboard',
  },
  inspiration_copied_prefix: {
    'zh-CN': '已复制: ',
    'en-US': 'Copied: ',
  },

  // 2. 开篇钩子库
  inspiration_hook_desc: {
    'zh-CN': '黄金三章节奏拍点公式库：精选 10 款经实战检验的起步钩子，点击卡片右上角可直接复制前三章节奏模板。',
    'en-US': 'First-Three-Chapters Pacing Formula: 10 battle-tested opening hooks. Click the card button to copy the 3-chapter beat outline.',
  },
  inspiration_hook_first_300: {
    'zh-CN': '前 300 字切入：',
    'en-US': 'First 300 words hook: ',
  },
  inspiration_hook_ch1: {
    'zh-CN': '第 1 章钩子：',
    'en-US': 'Chapter 1 Hook: ',
  },
  inspiration_hook_ch2: {
    'zh-CN': '第 2 章反转：',
    'en-US': 'Chapter 2 Twist: ',
  },
  inspiration_hook_ch3: {
    'zh-CN': '第 3 章高潮：',
    'en-US': 'Chapter 3 Climax: ',
  },
  inspiration_hook_btn_copy: {
    'zh-CN': '复制本套三章细纲',
    'en-US': 'Copy 3-Chapter Beat Outline',
  },

  // 3. 金手指机制库
  inspiration_gf_desc: {
    'zh-CN': '12 大经典外挂设定库：包含触发机制、成长曲线、使用限制与防战力崩坏铁律，帮助设定有代偿、有深度、不廉价的核心金手指。',
    'en-US': '12 Classic Cheat Mechanics: trigger mechanisms, progression curves, limitations, and power-creep iron rules for deep, non-trivial core setups.',
  },
  inspiration_gf_trigger: {
    'zh-CN': '触发机制：',
    'en-US': 'Trigger Mechanism: ',
  },
  inspiration_gf_curve: {
    'zh-CN': '成长曲线：',
    'en-US': 'Progression Curve: ',
  },
  inspiration_gf_cost: {
    'zh-CN': '代价与限制：',
    'en-US': 'Costs & Limits: ',
  },
  inspiration_gf_anticollapse: {
    'zh-CN': '防崩盘铁律：',
    'en-US': 'Anti-Collapse Iron Rule: ',
  },
  inspiration_gf_btn_copy: {
    'zh-CN': '复制金手指设定',
    'en-US': 'Copy Cheat Setup',
  },

  // 4. 爽点打脸设计库
  inspiration_sd_desc: {
    'zh-CN': '网文爽点与打脸逆袭闭环设计库：覆盖 12 大成熟爽点模式，包含三段式闭环（压抑-蓄势-释放）、打脸四拍（嘲讽-沉默-碾压-围观）及升级防疲劳链。',
    'en-US': 'Webnovel Catharsis & Climax Design: 12 mature catharsis tropes, 3-stage loop (Suppression-Buildup-Release), 4-beat execution, and anti-fatigue escalation chains.',
  },
  inspiration_sd_suppression: {
    'zh-CN': '【压抑前奏】',
    'en-US': '[Suppression Prelude]',
  },
  inspiration_sd_buildup: {
    'zh-CN': '【暗中蓄势】',
    'en-US': '[Hidden Buildup]',
  },
  inspiration_sd_fourbeats: {
    'zh-CN': '打脸四拍执行节拍：',
    'en-US': 'Catharsis 4-Beat Pacing:',
  },
  inspiration_sd_upgradepath: {
    'zh-CN': '升级路径：',
    'en-US': 'Escalation Path: ',
  },
  inspiration_sd_antifatigue: {
    'zh-CN': '防疲劳提示：',
    'en-US': 'Anti-Fatigue Tip: ',
  },
  inspiration_sd_btn_copy: {
    'zh-CN': '复制本套爽点模型',
    'en-US': 'Copy Trope Model',
  },

  // 5. 世界观体系库
  inspiration_wd_desc: {
    'zh-CN': '多题材世界观与力量体系设定库：包含清晰境界阶梯、三大不可违背法则铁律、货币资源兑换链及战力防崩红线。',
    'en-US': 'Multigenre Worldbuilding & Power Systems: clear progression tiers, unbreakable iron laws, currency/resource conversion, and power creep safeguards.',
  },
  inspiration_wd_ladder: {
    'zh-CN': '境界进阶阶梯：',
    'en-US': 'Progression Ladder:',
  },
  inspiration_wd_power: {
    'zh-CN': '能力：',
    'en-US': 'Power: ',
  },
  inspiration_wd_cost: {
    'zh-CN': '代价：',
    'en-US': 'Cost: ',
  },
  inspiration_wd_ironrules: {
    'zh-CN': '法则铁律：',
    'en-US': 'Iron Rules:',
  },
  inspiration_wd_currency: {
    'zh-CN': '货币与资源：',
    'en-US': 'Currencies & Resources: ',
  },
  inspiration_wd_collapsewarning: {
    'zh-CN': '防崩红线：',
    'en-US': 'Power Creep Warning Line: ',
  },
  inspiration_wd_btn_copy: {
    'zh-CN': '复制世界观设定',
    'en-US': 'Copy World Setting',
  },

  // 6. 名场面台词库
  inspiration_dlg_desc: {
    'zh-CN': '名场面金句与反AI台词设计库：精选 12 大经典高频交锋场景，提供【AI书面腔反例】与【真人网文口语台词】对照，拆解潜台词、动作节拍与语言指纹。',
    'en-US': 'Signature Dialogue & Anti-Slop Library: 12 classic confrontational scenes contrasting AI expository clichés against vivid humanized spoken dialogue, with subtext, action beats, and speech profiles.',
  },
  inspiration_dlg_ai_bad: {
    'zh-CN': '❌ AI说明文书面腔（反例）：',
    'en-US': '❌ AI Expository Cliche (Negative Example):',
  },
  inspiration_dlg_human_good: {
    'zh-CN': '✅ 顶级网文口语台词（推荐）：',
    'en-US': '✅ Vivid Spoken Dialogue (Recommended):',
  },
  inspiration_dlg_subtext: {
    'zh-CN': '【潜台词拆解】',
    'en-US': '[Subtext Breakdown]',
  },
  inspiration_dlg_actions: {
    'zh-CN': '【神态动作搭配】',
    'en-US': '[Action & Facial Beats]',
  },
  inspiration_dlg_speechtip: {
    'zh-CN': '【语言指纹建议】',
    'en-US': '[Speech Profile Tip]',
  },
  inspiration_dlg_btn_copy: {
    'zh-CN': '复制台词与动作',
    'en-US': 'Copy Dialogue & Beats',
  },

  // 7. 爆款人设矩阵
  inspiration_chr_desc: {
    'zh-CN': '爆款人设反差矩阵：提炼 12 大成熟立体的网文角色原型，以表面伪装 vs 隐藏反差构筑张力，防脸谱化、降智与人设崩塌。',
    'en-US': 'Viral Character Persona Matrix: 12 multi-dimensional character archetypes utilizing surface mask vs hidden contrast to prevent flat stereotypes and out-of-character drift.',
  },
  inspiration_chr_surface: {
    'zh-CN': '【表面标签】',
    'en-US': '[Surface Persona]',
  },
  inspiration_chr_contrast: {
    'zh-CN': '【隐藏反差】',
    'en-US': '[Hidden Contrast]',
  },
  inspiration_chr_desire: {
    'zh-CN': '【核心欲望】',
    'en-US': '[Core Motivation]',
  },
  inspiration_chr_flaw: {
    'zh-CN': '【致命弱点】',
    'en-US': '[Fatal Flaw]',
  },
  inspiration_chr_anticollapse: {
    'zh-CN': '【防崩铁律】',
    'en-US': '[Anti-OOC Iron Rule]',
  },
  inspiration_chr_action: {
    'zh-CN': '【高光动作】',
    'en-US': '[Signature Action / Catchphrase]',
  },
  inspiration_chr_arc: {
    'zh-CN': '【成长轨迹】',
    'en-US': '[Character Arc]',
  },
  inspiration_chr_btn_copy: {
    'zh-CN': '复制完整人设卡',
    'en-US': 'Copy Full Persona Card',
  },
  inspiration_chr_copied_card: {
    'zh-CN': '已复制人设卡: ',
    'en-US': 'Copied Persona Card: ',
  },

  // 8. 情绪高潮演出
  inspiration_emt_desc: {
    'zh-CN': '情绪高潮演出与五感通感库：专治网文 AI 味直白喊情绪（他很愤怒/我好难过），以微表情、心跳冷汗、环境共鸣将情绪演出来。',
    'en-US': 'Emotional Climax & Sensory Show-Don\'t-Tell: cures AI-style blunt emotion telling through micro-expressions, visceral physiological reactions, and atmospheric resonance.',
  },
  inspiration_emt_ai_bad: {
    'zh-CN': '❌ AI直白喊情绪（反例）：',
    'en-US': '❌ AI Blunt Telling (Negative Example):',
  },
  inspiration_emt_human_good: {
    'zh-CN': '✅ 顶级网文高潮演出正文（示范）：',
    'en-US': '✅ Evocative Scene Show-Don\'t-Tell (Recommended):',
  },
  inspiration_emt_vision: {
    'zh-CN': '【视觉微表情】',
    'en-US': '[Visual & Micro-Expressions]',
  },
  inspiration_emt_physio: {
    'zh-CN': '【生理本能反应】',
    'en-US': '[Physiological Reactions]',
  },
  inspiration_emt_touch: {
    'zh-CN': '【触觉与温感】',
    'en-US': '[Touch & Temperature]',
  },
  inspiration_emt_sound: {
    'zh-CN': '【听觉与空白】',
    'en-US': '[Sound & Silence]',
  },
  inspiration_emt_env: {
    'zh-CN': '【环境通感渲染】',
    'en-US': '[Atmospheric Resonance]',
  },
  inspiration_emt_rhythm: {
    'zh-CN': '【节拍秘籍】',
    'en-US': '[Pacing & Rhythm Secret]',
  },
  inspiration_emt_btn_copy: {
    'zh-CN': '复制范例与五感细节',
    'en-US': 'Copy Sample & Sensory Details',
  },
  inspiration_emt_copied_scene: {
    'zh-CN': '已复制情绪范例: ',
    'en-US': 'Copied Emotion Sample: ',
  },

  // 小说精华数据库 (EssenceWorkbench) - 五大顶层标签页
  essence_tab_macro: {
    'zh-CN': '离线精读与解构提炼',
    'en-US': 'Offline Deep Read & Extraction',
  },
  essence_tab_assets: {
    'zh-CN': '五维精华资产库',
    'en-US': '5D Essence Asset Matrix',
  },
  essence_tab_chains: {
    'zh-CN': '伏笔暗线图谱',
    'en-US': 'Foreshadowing & Plot Chains',
  },
  essence_tab_books: {
    'zh-CN': '已精读书籍档案',
    'en-US': 'Archived Masterpiece Books',
  },
  essence_tab_constitution: {
    'zh-CN': '宪法正典审查',
    'en-US': 'Canon Guard & Constitution',
  },
  // 精华库总览（书籍页顶部四项指标）
  essence_stats_books: {
    'zh-CN': '精读著作',
    'en-US': 'Studied Books',
  },
  essence_stats_chars: {
    'zh-CN': '总字数',
    'en-US': 'Total Characters',
  },
  essence_stats_assets: {
    'zh-CN': '五维资产',
    'en-US': 'Five-Axis Assets',
  },
  essence_stats_chains: {
    'zh-CN': '伏笔暗线',
    'en-US': 'Foreshadow Chains',
  },

  // 五维分类
  essence_cat_all: {
    'zh-CN': '全部五维分类',
    'en-US': 'All 5D Categories',
  },
  essence_cat_outline: {
    'zh-CN': '骨架大纲',
    'en-US': 'Structural Outline',
  },
  essence_cat_hook: {
    'zh-CN': '开篇钩子',
    'en-US': 'Opening Hook',
  },
  essence_cat_character: {
    'zh-CN': '人设反差',
    'en-US': 'Character Persona',
  },
  essence_cat_trope: {
    'zh-CN': '爆款桥段',
    'en-US': 'Viral Trope',
  },
  essence_cat_style: {
    'zh-CN': '反AI口语',
    'en-US': 'Anti-Slop Dialogue',
  },

  // 1. 离线精读与宏观解构提炼
  essence_macro_desc: {
    'zh-CN': '100% 纯本地离线精读引擎：对长篇正文进行章节切片、黄金三章钩子探测、对白与叙述比例核算、高频反 AI 口语词频统计，提炼出可直接反哺创作的五维结构化资产。',
    'en-US': '100% pure local offline deep reading engine: parses chapters, detects opening hooks, calculates dialogue ratios, and identifies anti-slop patterns to distill 5D reusable assets.',
  },
  essence_macro_title_label: {
    'zh-CN': '精图书籍/样本名称',
    'en-US': 'Sample Book Name',
  },
  essence_macro_title_placeholder: {
    'zh-CN': '例如：《宿命之环》《我在精神病院学斩神》',
    'en-US': 'e.g. Mistborn, Cradle, Lord of the Mysteries',
  },
  essence_macro_platform_label: {
    'zh-CN': '目标平台生态',
    'en-US': 'Target Platform Ecosystem',
  },
  essence_macro_genre_label: {
    'zh-CN': '所属题材类别',
    'en-US': 'Genre Category',
  },
  essence_macro_text_label: {
    'zh-CN': '输入精读正文（支持多章连粘，自动识别章节序号）',
    'en-US': 'Input Draft/Sample Text (multiple chapters supported)',
  },
  essence_macro_text_placeholder: {
    'zh-CN': '粘贴小说样本文字...',
    'en-US': 'Paste novel draft or sample text...',
  },
  essence_macro_btn_start: {
    'zh-CN': '开始深度精读与宏观解构',
    'en-US': 'Start Deep Read & Extraction',
  },
  essence_macro_btn_analyzing: {
    'zh-CN': '离线深度精读分析中...',
    'en-US': 'Analyzing offline...',
  },
  essence_macro_report_chip: {
    'zh-CN': '精读提炼报告',
    'en-US': 'Extraction Report',
  },
  essence_macro_metric_chapters: {
    'zh-CN': '总解析章节',
    'en-US': 'Parsed Chapters',
  },
  essence_macro_metric_words: {
    'zh-CN': '总精读字数',
    'en-US': 'Total Word Count',
  },
  essence_macro_metric_avg_words: {
    'zh-CN': '平均章字数',
    'en-US': 'Avg Chapter Words',
  },
  essence_macro_metric_dialogue_ratio: {
    'zh-CN': '对白占比',
    'en-US': 'Dialogue Ratio',
  },
  essence_macro_metric_climax_interval: {
    'zh-CN': '高潮节奏周期',
    'en-US': 'Climax Pacing Interval',
  },
  essence_macro_metric_ai_slop: {
    'zh-CN': 'AI 味指数 (0-10)',
    'en-US': 'AI Slop Index (0-10)',
  },
  essence_macro_h3_opening: {
    'zh-CN': '黄金三章开篇解构（抓人感与钩子演进）',
    'en-US': 'First 3 Chapters Hook Deconstruction',
  },
  essence_macro_h3_speech: {
    'zh-CN': '高频真实网感口语 / 特色句式',
    'en-US': 'Vivid Humanized Dialogue Patterns',
  },
  essence_macro_h3_suggested: {
    'zh-CN': '结构化资产建议（点击一键沉淀入库）',
    'en-US': 'Suggested Structured Assets',
  },
  essence_macro_btn_save_asset: {
    'zh-CN': '沉淀入库',
    'en-US': 'Save Asset',
  },
  essence_macro_toast_done: {
    'zh-CN': '深度精读与宏观提炼完成，已建立书籍档案！',
    'en-US': 'Deep reading and macro extraction complete. Book archive created!',
  },
  essence_macro_toast_saved: {
    'zh-CN': '已成功入库资产：',
    'en-US': 'Asset saved successfully: ',
  },

  // 2. 五维精华资产库
  essence_assets_category_filter: {
    'zh-CN': '五维分类',
    'en-US': '5D Category',
  },
  essence_assets_platform_filter: {
    'zh-CN': '生态平台',
    'en-US': 'Platform Ecosystem',
  },
  essence_assets_all_platforms: {
    'zh-CN': '全平台生态',
    'en-US': 'All Platforms',
  },
  essence_assets_search_placeholder: {
    'zh-CN': '模糊检索 (标题/标签/摘要)',
    'en-US': 'Search (Title, Tags, Summary)',
  },
  essence_assets_btn_refresh: {
    'zh-CN': '刷新',
    'en-US': 'Refresh',
  },
  essence_assets_empty: {
    'zh-CN': '暂无符合条件的精读资产。可在「离线精读与解构提炼」页签粘贴正文进行智能分析萃取。',
    'en-US': 'No matching essence assets found. Extract from sample texts in the extraction tab.',
  },
  essence_assets_platform_prefix: {
    'zh-CN': '生态: ',
    'en-US': 'Platform: ',
  },
  essence_assets_genre_prefix: {
    'zh-CN': '题材: ',
    'en-US': 'Genre: ',
  },
  essence_assets_note_prefix: {
    'zh-CN': '创作者感悟: ',
    'en-US': 'Creator Note: ',
  },
  essence_assets_btn_delete: {
    'zh-CN': '删除',
    'en-US': 'Delete',
  },
  essence_assets_btn_adopt: {
    'zh-CN': '一键反哺创作',
    'en-US': 'Adopt to Project',
  },
  essence_assets_adopt_title: {
    'zh-CN': '一键反哺至写作工坊',
    'en-US': 'Adopt Asset to Writing Project',
  },
  essence_assets_adopt_target_project: {
    'zh-CN': '目标项目',
    'en-US': 'Target Project',
  },
  essence_assets_adopt_target_kind: {
    'zh-CN': '反哺转存形态',
    'en-US': 'Target Entity',
  },
  essence_assets_adopt_kind_outline: {
    'zh-CN': '转入写作大纲 (writing_outlines)',
    'en-US': 'Inject as Outline (writing_outlines)',
  },
  essence_assets_adopt_kind_character: {
    'zh-CN': '转入人物卡片 (writing_characters)',
    'en-US': 'Inject as Character (writing_characters)',
  },
  essence_assets_adopt_kind_note: {
    'zh-CN': '转入灵感便签 (writing_notes)',
    'en-US': 'Inject as Inspiration Note (writing_notes)',
  },
  essence_assets_adopt_btn_cancel: {
    'zh-CN': '取消',
    'en-US': 'Cancel',
  },
  essence_assets_adopt_btn_confirm: {
    'zh-CN': '确认反哺',
    'en-US': 'Confirm Adoption',
  },

  // 3. 已精读书籍档案
  essence_books_desc: {
    'zh-CN': '本地精读档案库：沉淀每部精读长篇的字数、对白率、节奏模型，支持全生命周期管理与结构化提纲导出。',
    'en-US': 'Local Masterpiece Archive: records word count, dialogue ratios, and rhythm models, supporting lifecycle management and outline export.',
  },
  essence_books_btn_refresh: {
    'zh-CN': '刷新档案',
    'en-US': 'Refresh Archives',
  },
  essence_books_empty: {
    'zh-CN': '暂无已精读的书籍档案。请先在「离线精读与解构提炼」页签输入样本进行解析。',
    'en-US': 'No archived books found. Extract sample text first.',
  },
  essence_books_dialogue_ratio: {
    'zh-CN': '对白占比: ',
    'en-US': 'Dialogue Ratio: ',
  },
  essence_books_climax_interval: {
    'zh-CN': '高潮间隔: ',
    'en-US': 'Climax Interval: ',
  },
  essence_books_ai_slop: {
    'zh-CN': 'AI 味道评分: ',
    'en-US': 'AI Slop Score: ',
  },
  essence_books_btn_export_outline: {
    'zh-CN': '导出大纲',
    'en-US': 'Export Outline',
  },
  essence_books_btn_export_beats: {
    'zh-CN': '导出节拍',
    'en-US': 'Export Beats',
  },
  essence_books_btn_adopt_book: {
    'zh-CN': '整本反哺',
    'en-US': 'Adopt Entire Book',
  },
  essence_books_adopt_title: {
    'zh-CN': '一键整本反哺到写作工坊',
    'en-US': 'Adopt Full Book Assets to Writing Project',
  },
  essence_books_adopt_target: {
    'zh-CN': '目标创作项目',
    'en-US': 'Target Writing Project',
  },
  essence_books_adopt_btn_confirm: {
    'zh-CN': '确认注入',
    'en-US': 'Confirm Injection',
  },
  essence_books_adopt_btn_adopting: {
    'zh-CN': '正在注入...',
    'en-US': 'Injecting...',
  },

  // 4. 伏笔暗线图谱
  essence_chains_filter_book: {
    'zh-CN': '筛选书籍档案',
    'en-US': 'Filter by Book',
  },
  essence_chains_all_books: {
    'zh-CN': '全部书籍暗线',
    'en-US': 'All Book Plot Chains',
  },
  essence_chains_btn_refresh: {
    'zh-CN': '刷新',
    'en-US': 'Refresh',
  },
  essence_chains_btn_create: {
    'zh-CN': '录入伏笔暗线',
    'en-US': 'New Plot Chain',
  },
  essence_chains_empty: {
    'zh-CN': '暂无伏笔暗线数据。点击右上角「录入伏笔暗线」，建立长篇小说的草蛇灰线与回收图谱。',
    'en-US': 'No plot chains found. Click "New Plot Chain" to record foreshadowing loops.',
  },
  essence_chains_plant_ch: {
    'zh-CN': '🌱 埋设：',
    'en-US': '🌱 Plant: ',
  },
  essence_chains_reveal_ch: {
    'zh-CN': '🔍 揭晓：',
    'en-US': '🔍 Reveal: ',
  },
  essence_chains_climax_ch: {
    'zh-CN': '💥 高潮回收：',
    'en-US': '💥 Climax Payoff: ',
  },
  essence_chains_dialog_title: {
    'zh-CN': '录入伏笔暗线与收敛图谱',
    'en-US': 'Record Plot Chain & Foreshadowing Loop',
  },
  essence_chains_form_book: {
    'zh-CN': '所属书籍',
    'en-US': 'Book',
  },
  essence_chains_form_title: {
    'zh-CN': '伏笔暗线名称',
    'en-US': 'Chain Title',
  },
  essence_chains_form_category: {
    'zh-CN': '伏笔类型',
    'en-US': 'Category',
  },
  essence_chains_form_plant: {
    'zh-CN': '埋下章节 (Plant)',
    'en-US': 'Plant Chapter',
  },
  essence_chains_form_reveal: {
    'zh-CN': '显露章节 (Reveal)',
    'en-US': 'Reveal Chapter',
  },
  essence_chains_form_climax: {
    'zh-CN': '高潮章节 (Climax)',
    'en-US': 'Climax Chapter',
  },
  essence_chains_form_status: {
    'zh-CN': '当前状态',
    'en-US': 'Current Status',
  },
  essence_chains_form_desc: {
    'zh-CN': '暗线铺设逻辑与爽点释放机制',
    'en-US': 'Foreshadowing & Payoff Mechanism',
  },
  essence_chains_status_planted: {
    'zh-CN': '🌱 已埋下',
    'en-US': '🌱 Planted',
  },
  essence_chains_status_developing: {
    'zh-CN': '⏳ 推进发酵',
    'en-US': '⏳ Developing',
  },
  essence_chains_status_revealed: {
    'zh-CN': '🔍 已显露',
    'en-US': '🔍 Revealed',
  },
  essence_chains_status_recycled: {
    'zh-CN': '✅ 闭环回收',
    'en-US': '✅ Recycled / Paid Off',
  },

  // 5. 小说宪法正典审查
  essence_const_title: {
    'zh-CN': '小说宪法正典审查 (Canon Guard)',
    'en-US': 'Novel Constitution & Canon Guard',
  },
  essence_const_desc: {
    'zh-CN': '审查世界观底线（严禁修仙/灵气/系统等超自然穿帮、严禁时代脱节科技词、严禁恶俗网文毒点台词），并可校验角色声线禁语（该角色绝不应说的话）。',
    'en-US': 'Audits core canon boundaries (anti-anachronism, supernatural slips, immersion-breaking tropes) and character voice taboo constraints.',
  },
  essence_const_text_label: {
    'zh-CN': '待审查小说正文或章节文本',
    'en-US': 'Draft Text or Chapter to Audit',
  },
  essence_const_text_placeholder: {
    'zh-CN': '粘贴待审查的段落或完整章节内容...',
    'en-US': 'Paste chapter draft or passage to audit...',
  },
  essence_const_voice_label: {
    'zh-CN': '自定义角色声线禁语 (可选，每行一条: 角色名: 禁语1, 禁语2)',
    'en-US': 'Custom Character Voice Taboos (Optional, e.g. Name: taboo1, taboo2)',
  },
  essence_const_voice_helper: {
    'zh-CN': '配置特定角色绝不会说的词汇或口癖，防止人设塌房与语调失真',
    'en-US': 'Defines words that specific characters would never say to prevent OOC voice drift',
  },
  essence_const_btn_check: {
    'zh-CN': '开始宪法正典审查',
    'en-US': 'Run Canon Guard Check',
  },
  essence_const_btn_checking: {
    'zh-CN': '审查中...',
    'en-US': 'Auditing...',
  },
  essence_const_chip_compliant: {
    'zh-CN': '✅ 宪法正典合规',
    'en-US': '✅ Canon Compliant',
  },
  essence_const_chip_violation: {
    'zh-CN': '⚠️ 存在违宪/破格隐患',
    'en-US': '⚠️ Canon Violations Detected',
  },
  essence_const_score_label: {
    'zh-CN': '合规得分: ',
    'en-US': 'Compliance Score: ',
  },
  essence_const_violations_h: {
    'zh-CN': '世界观与底线偏离列表',
    'en-US': 'Canon & Worldbuilding Violations',
  },
  essence_const_no_violations: {
    'zh-CN': '🎉 未发现任何超自然穿帮、时代脱节或毒点台词！',
    'en-US': '🎉 No canon violations or anachronisms found!',
  },
  essence_const_voice_h: {
    'zh-CN': '角色声线禁语冲突',
    'en-US': 'Character Voice Taboo Alerts',
  },
  essence_const_no_voice_alerts: {
    'zh-CN': '✨ 未检测到任何角色人设禁语冲突。',
    'en-US': '✨ No character voice violations detected.',
  },

  // =========================================================================
  // QualityWorkbench 质检工作台双语国际化词典 (Milestone 21)
  // =========================================================================
  // 顶层标签页
  quality_tab_check: {
    'zh-CN': '单章检查',
    'en-US': 'Chapter Check',
  },
  quality_tab_book: {
    'zh-CN': '全书质检',
    'en-US': 'Full Book Inspection',
  },
  quality_tab_qc: {
    'zh-CN': 'QC 综合',
    'en-US': 'Comprehensive QC',
  },
  quality_tab_poison: {
    'zh-CN': '毒点避雷',
    'en-US': 'Poison & Trope Defense',
  },

  // 判定与状态枚举
  quality_verdict_pass: {
    'zh-CN': '通过',
    'en-US': 'PASS',
  },
  quality_verdict_warn: {
    'zh-CN': '警告',
    'en-US': 'WARN',
  },
  quality_verdict_fail: {
    'zh-CN': '不通过',
    'en-US': 'FAIL',
  },
  quality_status_pending: {
    'zh-CN': '等待中',
    'en-US': 'Pending',
  },
  quality_status_running: {
    'zh-CN': '运行中',
    'en-US': 'Running',
  },
  quality_status_done: {
    'zh-CN': '已完成',
    'en-US': 'Completed',
  },
  quality_status_error: {
    'zh-CN': '失败',
    'en-US': 'Failed',
  },

  // 桌面端路径选择
  quality_btn_pick_dir: {
    'zh-CN': '选择目录…',
    'en-US': 'Select Directory…',
  },
  quality_btn_pick_file: {
    'zh-CN': '选择文件…',
    'en-US': 'Select File…',
  },

  // 1. 单章检查
  quality_check_title: {
    'zh-CN': '单章检查',
    'en-US': 'Single Chapter Quality Check',
  },
  quality_check_empty_title: {
    'zh-CN': '还没有检查结果',
    'en-US': 'No results yet',
  },
  quality_check_empty_hint: {
    'zh-CN': '填入章节路径或粘贴正文后点检查',
    'en-US': 'Enter a chapter path or paste text, then click Check',
  },
  quality_check_target_label: {
    'zh-CN': '章节路径（或粘贴文本）',
    'en-US': 'Chapter Path (or Paste Draft)',
  },
  quality_check_voice_label: {
    'zh-CN': 'voice-card（可选）',
    'en-US': 'Voice Card (Optional)',
  },
  quality_check_genre_label: {
    'zh-CN': 'genre-pack（可选）',
    'en-US': 'Genre Pack (Optional)',
  },
  quality_check_option_none: {
    'zh-CN': '无',
    'en-US': 'None',
  },
  quality_check_btn_start: {
    'zh-CN': '检查',
    'en-US': 'Check',
  },
  quality_check_btn_checking: {
    'zh-CN': '检查中...',
    'en-US': 'Checking...',
  },
  quality_check_text_label: {
    'zh-CN': '或粘贴章节正文',
    'en-US': 'Or Paste Chapter Text',
  },
  quality_check_score_quality: {
    'zh-CN': '章节质量：',
    'en-US': 'Chapter Quality: ',
  },
  quality_check_score_consistency: {
    'zh-CN': '一致性：',
    'en-US': 'Consistency: ',
  },
  quality_check_load_asset_failed: {
    'zh-CN': '加载资产失败: ',
    'en-US': 'Failed to load assets: ',
  },

  // 2. 全书质检
  quality_book_title: {
    'zh-CN': '全书质检',
    'en-US': 'Full Book Quality Inspection',
  },
  quality_book_target_label: {
    'zh-CN': '章节目录路径',
    'en-US': 'Chapters Directory Path',
  },
  quality_book_btn_start: {
    'zh-CN': '质检',
    'en-US': 'Inspect',
  },
  quality_book_btn_inspecting: {
    'zh-CN': '质检中...',
    'en-US': 'Inspecting...',
  },
  quality_book_verdict_label: {
    'zh-CN': '判定：',
    'en-US': 'Verdict: ',
  },
  quality_book_collapse: {
    'zh-CN': '收起',
    'en-US': 'Collapse',
  },

  // 3. QC 综合
  quality_qc_title: {
    'zh-CN': 'QC 综合质检（四层十二维）',
    'en-US': 'Comprehensive QC (4-Layer 12-Dimensional)',
  },
  quality_qc_target_label: {
    'zh-CN': '章节目录路径',
    'en-US': 'Chapters Directory Path',
  },
  quality_qc_btn_start: {
    'zh-CN': '开始 QC',
    'en-US': 'Start QC',
  },
  quality_qc_btn_running: {
    'zh-CN': 'QC 运行中...',
    'en-US': 'QC Running...',
  },
  quality_qc_status_label: {
    'zh-CN': '状态：',
    'en-US': 'Status: ',
  },
  quality_qc_verdict_label: {
    'zh-CN': '判定：',
    'en-US': 'Verdict: ',
  },
  quality_qc_score_label: {
    'zh-CN': '总分 ',
    'en-US': 'Total Score: ',
  },
  quality_qc_layer_suffix: {
    'zh-CN': ' 维',
    'en-US': ' Dim',
  },
  quality_qc_score_suffix: {
    'zh-CN': '分',
    'en-US': ' pts',
  },
  quality_qc_report_saved: {
    'zh-CN': '报告已落盘：',
    'en-US': 'Report saved to disk: ',
  },
  quality_qc_history_title: {
    'zh-CN': '历史报告',
    'en-US': 'Historical QC Reports',
  },

  // =========================================================================
  // AssetLibrary 资产库与资产全品类矩阵浏览双语国际化词典 (Milestone 22)
  // =========================================================================
  asset_lib_title: {
    'zh-CN': '资产库',
    'en-US': 'Asset Library & Matrix',
  },
  asset_lib_filter_all: {
    'zh-CN': '全部',
    'en-US': 'All',
  },
  // 题材包与文风卡成对存在且同名，列表里用这两个标签点明分工
  asset_lib_pack_tag: {
    'zh-CN': '· 规则包（注入用）',
    'en-US': '· rule pack (injected)',
  },
  asset_lib_prose_tag: {
    'zh-CN': '· 风格样本（参照用）',
    'en-US': '· style sample (reference)',
  },
  asset_lib_load_failed: {
    'zh-CN': '加载失败：',
    'en-US': 'Failed to load assets: ',
  },
  asset_lib_empty: {
    'zh-CN': '暂无资产',
    'en-US': 'No assets found',
  },
  asset_lib_empty_hint: {
    'zh-CN': '先去分析拆书，完成后再回来查看',
    'en-US': 'Analyze a book first, then return here',
  },
  asset_lib_empty_hint_filtered: {
    'zh-CN': '该类型暂无资产，换个分类试试',
    'en-US': 'No assets in this category, try another filter',
  },
  asset_lib_empty_cta: {
    'zh-CN': '去分析',
    'en-US': 'Go to Analysis',
  },
  asset_lib_select_hint: {
    'zh-CN': '从左侧选择一个资产查看详情',
    'en-US': 'Select an asset from the list to view details',
  },
  asset_lib_raw_data: {
    'zh-CN': '高级 · 查看原始数据',
    'en-US': 'Advanced · View Raw Data',
  },

  // 11 大核心资产类型标签
  asset_kind_voice: {
    'zh-CN': '声线卡',
    'en-US': 'Voice Card',
  },
  asset_kind_structure: {
    'zh-CN': '结构观测',
    'en-US': 'Structure Observation',
  },
  asset_kind_commercial: {
    'zh-CN': '商业观测',
    'en-US': 'Commercial Observation',
  },
  asset_kind_craft: {
    'zh-CN': '笔法卡',
    'en-US': 'Craft Card',
  },
  asset_kind_genre_pack: {
    'zh-CN': '题材包',
    'en-US': 'Genre Pack',
  },
  asset_kind_prose_card: {
    'zh-CN': '文风卡',
    'en-US': 'Prose Card',
  },
  asset_kind_distilled: {
    'zh-CN': '蒸馏规则',
    'en-US': 'Distilled Rule',
  },
  asset_kind_prose_card_index: {
    'zh-CN': '题材文风卡索引',
    'en-US': 'Genre Prose Index',
  },
  asset_kind_trope: {
    'zh-CN': '桥段',
    'en-US': 'Trope',
  },
  asset_kind_report: {
    'zh-CN': '报告',
    'en-US': 'Report',
  },
  asset_kind_book: {
    'zh-CN': '语料',
    'en-US': 'Corpus Book',
  },

  // 列表层的「这是什么」一句话说明（asset_lib 卡片直接用，避免点进去才知道）
  asset_purpose_voice: {
    'zh-CN': '记录一本书的叙述声线与语言风格：人称、句式节奏、对白特征、情绪处理与禁用词。',
    'en-US': 'One book\'s narrative voice: POV, sentence rhythm, dialogue traits, emotional handling and banned wording.',
  },
  asset_purpose_structure: {
    'zh-CN': '记录一本书的章节结构规律：钩子间隔、高潮周期、伏笔跨度。',
    'en-US': 'One book\'s structural patterns: hook spacing, climax cycle, foreshadowing span.',
  },
  asset_purpose_commercial: {
    'zh-CN': '记录一本书的商业节奏：爽点密度与类型、付费卡点、铺垫长度。',
    'en-US': 'One book\'s commercial rhythm: payoff density and types, paywall points, buildup length.',
  },
  asset_purpose_craft: {
    'zh-CN': '记录一本书的写作技法：伏笔、转场、对白、感官描写与可复用模式。',
    'en-US': 'One book\'s craft techniques: foreshadowing, transitions, dialogue, sensory writing and reusable patterns.',
  },
  asset_purpose_genre_pack: {
    'zh-CN': '题材级规则包：结构、商业、质检阈值、语言铁律与世界观约定，写作时直接注入。',
    'en-US': 'Genre-level rule pack: structure, commercial rhythm, quality thresholds, hard language rules and world conventions; injected when writing.',
  },
  asset_purpose_prose_card: {
    'zh-CN': '题材级风格样本：该题材整体的行文风格原文，供写作时参照，不直接注入。',
    'en-US': 'Genre-level style sample: reference prose for the whole genre; read for reference, not injected.',
  },
  asset_purpose_distilled: {
    'zh-CN': '多本书聚合出的共性规则：必守硬边界、高置信建议与分歧，自动拼入写作 prompt。',
    'en-US': 'Cross-book aggregated rules: hard boundaries, high-confidence suggestions and disagreements; merged into the writing prompt.',
  },
  asset_purpose_prose_card_index: {
    'zh-CN': '题材文风卡的寻址索引：题材名 → 卡片文件，系统内部使用。',
    'en-US': 'Lookup index mapping genre name to prose card file; used internally.',
  },
  asset_purpose_trope: {
    'zh-CN': '桥段模式库：跨书跨题材的通用情节骨架，构思时检索调用。',
    'en-US': 'Trope library: reusable plot skeletons across books and genres, searched while plotting.',
  },
  asset_purpose_report: {
    'zh-CN': '拆书生成的万字报告与笔法分析。',
    'en-US': 'Ten-thousand-word dissection report and craft analysis generated from a book.',
  },
  asset_purpose_book: {
    'zh-CN': '导入的语料书籍（正文原文）。',
    'en-US': 'Imported corpus book (original text).',
  },

  // =========================================================================
  // HomeDashboard 首页仪表盘与系统全景矩阵双语国际化词典 (Milestone 23)
  // =========================================================================
  home_empty_title: {
    'zh-CN': '还没有任何书籍数据',
    'en-US': 'No book data yet',
  },
  home_empty_hint: {
    'zh-CN': '从「分析」页导入一本 TXT 开始拆书',
    'en-US': 'Import a TXT file from Deconstruct to begin analysis',
  },
  home_empty_cta: {
    'zh-CN': '去分析拆书',
    'en-US': 'Go to Deconstruct',
  },
  home_brand_title: {
    'zh-CN': '暮冬念春工作台',
    'en-US': 'Exoscribe Studio',
  },
  home_brand_subtitle: {
    'zh-CN': '中文书籍创作辅助系统',
    'en-US': 'Bilingual Narrative Exoskeleton & Writing Engine',
  },
  home_help_tooltip: {
    'zh-CN': '新手上路：从这里开始',
    'en-US': 'Quick Start Guide: Start Here',
  },
  home_help_aria: {
    'zh-CN': '新手上路',
    'en-US': 'Quick Start',
  },
  home_model_configured: {
    'zh-CN': '模型已配置',
    'en-US': 'Model Configured',
  },
  home_model_not_configured: {
    'zh-CN': '模型未配置',
    'en-US': 'Model Unconfigured',
  },
  home_model_alert: {
    'zh-CN': '尚未配置外部模型，请先运行 model_config.py 配置。',
    'en-US': 'External model not configured yet. Please run model_config.py to configure.',
  },

  // KPI 指标卡
  home_kpi_books: {
    'zh-CN': '已拆书',
    'en-US': 'Deconstructed Books',
  },
  home_kpi_genre_packs: {
    'zh-CN': '题材包',
    'en-US': 'Genre Packs',
  },
  home_kpi_reports: {
    'zh-CN': '报告',
    'en-US': 'Analysis Reports',
  },
  home_kpi_assets: {
    'zh-CN': '资产总数',
    'en-US': 'Total Assets',
  },

  // 资产分布
  home_asset_dist_title: {
    'zh-CN': '资产类型分布',
    'en-US': 'Asset Distribution',
  },
  home_asset_dist_empty: {
    'zh-CN': '暂无资产数据',
    'en-US': 'No asset data yet',
  },
  home_asset_dist_empty_sub: {
    'zh-CN': '拆书分析后自动生成',
    'en-US': 'Generated automatically after analysis',
  },

  // 快速操作
  home_quick_start_title: {
    'zh-CN': '开始创作',
    'en-US': 'Start Writing',
  },
  home_quick_action_analysis_title: {
    'zh-CN': '分析拆书',
    'en-US': 'Deconstruct',
  },
  home_quick_action_analysis_desc: {
    'zh-CN': '导入 TXT，全链路拆解',
    'en-US': 'Import TXT & full-pipeline deconstruction',
  },
  home_quick_action_assets_title: {
    'zh-CN': '资产库',
    'en-US': 'Asset Matrix',
  },
  home_quick_action_assets_desc: {
    'zh-CN': '浏览题材包与笔法卡',
    'en-US': 'Browse genre packs & craft cards',
  },
  home_quick_action_writing_title: {
    'zh-CN': '沉浸创作室',
    'en-US': 'Immersion Studio',
  },
  home_quick_action_writing_desc: {
    'zh-CN': '一屏三栏·副驾伴写',
    'en-US': '3-Column Workspace · AI Copilot',
  },
  home_quick_action_enter: {
    'zh-CN': '进入',
    'en-US': 'Enter',
  },
  home_recent_activity_title: {
    'zh-CN': '最近动态',
    'en-US': 'Recent Activity',
  },

  // 使用旅程进度条 (JourneyStepper — HomeDashboard)
  journey_title: {
    'zh-CN': '使用旅程',
    'en-US': 'Your Journey',
  },
  journey_subtitle: {
    'zh-CN': '点击任意一步前往对应工作台',
    'en-US': 'Click any step to jump to its workbench',
  },
  journey_progress: {
    'zh-CN': '{done} / {total} 已完成',
    'en-US': '{done} / {total} completed',
  },
  journey_step_model_hint: {
    'zh-CN': '前往系统页配置模型',
    'en-US': 'Go to System to configure a model',
  },
  journey_step_analyze_hint: {
    'zh-CN': '前往分析页导入并拆解',
    'en-US': 'Go to Analysis to import & deconstruct',
  },
  journey_step_write_qc_hint: {
    'zh-CN': '前往写作台新建章节并质检',
    'en-US': 'Go to Writing Studio to draft & QC',
  },

  // 拆书分析工坊 (Analysis View / Story Deconstruction)
  analysis_tab_import: {
    'zh-CN': '导入',
    'en-US': 'Import',
  },
  context_help_default: {
    'zh-CN': '查看此功能的使用指南',
    'en-US': 'View guide for this feature',
  },
  analysis_tab_progress: {
    'zh-CN': '进度',
    'en-US': 'Progress',
  },
  analysis_tab_result: {
    'zh-CN': '结果',
    'en-US': 'Results',
  },
  analysis_help_title: {
    'zh-CN': '查看拆书指南',
    'en-US': 'View Deconstruction Guide',
  },
  analysis_status_idle: {
    'zh-CN': '空闲',
    'en-US': 'Idle',
  },
  analysis_status_running: {
    'zh-CN': '运行中',
    'en-US': 'Running',
  },
  analysis_status_paused: {
    'zh-CN': '已暂停',
    'en-US': 'Paused',
  },
  analysis_status_done: {
    'zh-CN': '已完成',
    'en-US': 'Completed',
  },
  analysis_status_error: {
    'zh-CN': '出错',
    'en-US': 'Error',
  },
  analysis_batches_unit: {
    'zh-CN': '批',
    'en-US': 'batches',
  },
  analysis_need_book: {
    'zh-CN': '请先导入书籍',
    'en-US': 'Please import a book first',
  },
  analysis_need_file: {
    'zh-CN': '请先导入书籍文件',
    'en-US': 'Please import a book file first',
  },
  analysis_need_genre: {
    'zh-CN': '请选择题材分类',
    'en-US': 'Please select a genre',
  },
  analysis_need_model: {
    'zh-CN': '尚未配置模型，请先在设置中配置模型',
    'en-US': 'No model configured. Please set up a model in Settings first',
  },
  analysis_import_pdf_hint: {
    'zh-CN': '暂不支持 PDF 导入，请先用 Word/记事本另存为 .txt (UTF-8 编码)',
    'en-US': 'PDF import is not supported. Please save as .txt (UTF-8) via Word or Notepad first',
  },
  analysis_import_doc_hint: {
    'zh-CN': '暂不支持 Word 文档导入，请先另存为 .txt (UTF-8 编码)',
    'en-US': 'Word document import is not supported. Please save as .txt (UTF-8) first',
  },
  analysis_import_md_hint: {
    'zh-CN': '暂不支持 Markdown 导入，请先另存为 .txt (UTF-8 编码)',
    'en-US': 'Markdown import is not supported. Please save as .txt (UTF-8) first',
  },
  error_action_file_too_large: {
    'zh-CN': '文件过大(100MB上限)，请拆分后重试',
    'en-US': 'File too large (100MB limit). Please split the file and try again',
  },
  error_action_symlink_rejected: {
    'zh-CN': '不支持符号链接，请选择源文件本身',
    'en-US': 'Symbolic links are not supported. Please select the original file',
  },
  error_action_port_busy: {
    'zh-CN': '端口被占用，请关闭占用程序或更换端口后重试',
    'en-US': 'Port is busy. Please close the conflicting program or try another port',
  },

  analysis_genre_label: {
    'zh-CN': '题材 *',
    'en-US': 'Genre *',
  },
  analysis_err_load_genres: {
    'zh-CN': '题材列表加载失败，请刷新重试',
    'en-US': 'Failed to load genres, please refresh',
  },
  analysis_err_select_genre: {
    'zh-CN': '请选择题材',
    'en-US': 'Please select a genre',
  },
  analysis_genre_auto_hint: {
    'zh-CN': '已根据文件名自动识别为「{genre}」，可手动修改',
    'en-US': 'Auto-detected as "{genre}" from filename — you can change it',
  },
  analysis_btn_running: {
    'zh-CN': '分析中…',
    'en-US': 'Analyzing...',
  },
  analysis_btn_start: {
    'zh-CN': '一键分析',
    'en-US': 'One-Click Analysis',
  },
  analysis_card_empty: {
    'zh-CN': '暂无数据',
    'en-US': 'No data available',
  },
  analysis_report_load_error: {
    'zh-CN': '报告加载失败',
    'en-US': 'Failed to load report',
  },
  analysis_res_tab_overview: {
    'zh-CN': '资产卡',
    'en-US': 'Asset Cards',
  },
  analysis_res_tab_scores: {
    'zh-CN': '章节打分',
    'en-US': 'Chapter Scores',
  },
  analysis_res_tab_reports: {
    'zh-CN': '报告',
    'en-US': 'Reports',
  },
  analysis_card_voice: {
    'zh-CN': '声线卡',
    'en-US': 'Voice Card',
  },
  analysis_card_structure: {
    'zh-CN': '结构观测',
    'en-US': 'Structure Observation',
  },
  analysis_card_commercial: {
    'zh-CN': '商业观测',
    'en-US': 'Commercial Observation',
  },
  analysis_card_craft: {
    'zh-CN': '笔法卡',
    'en-US': 'Craft Card',
  },
  analysis_chart_consistency: {
    'zh-CN': '一致性',
    'en-US': 'Consistency',
  },
  analysis_chart_quality: {
    'zh-CN': '质量',
    'en-US': 'Quality',
  },
  analysis_chart_avg: {
    'zh-CN': '综合均分',
    'en-US': 'Overall Average',
  },
  analysis_score_bar_title: {
    'zh-CN': '章节打分对比',
    'en-US': 'Chapter Score Comparison',
  },
  analysis_score_radar_title: {
    'zh-CN': '综合能力雷达',
    'en-US': 'Comprehensive Ability Radar',
  },
  analysis_score_empty: {
    'zh-CN': '暂无章节打分数据',
    'en-US': 'No chapter score data',
  },
  analysis_no_book_hint: {
    'zh-CN': '请先在首页/控制栏导入并拆书，完成后在此查看结果',
    'en-US': 'Please import and analyze a book first to view results here',
  },
  analysis_load_failed: {
    'zh-CN': '加载失败',
    'en-US': 'Failed to load',
  },
  analysis_retry: {
    'zh-CN': '重试',
    'en-US': 'Retry',
  },
  analysis_current_book: {
    'zh-CN': '当前书籍',
    'en-US': 'Current Book',
  },
  analysis_not_generated: {
    'zh-CN': '尚未生成拆书结果，请先运行「一键分析」',
    'en-US': 'No analysis results generated yet. Please run "One-Click Analysis" first',
  },
  analysis_result_chip: {
    'zh-CN': '拆书结果',
    'en-US': 'Analysis Result',
  },
  analysis_reports_empty: {
    'zh-CN': '暂无报告',
    'en-US': 'No reports available',
  },
  analysis_report_item: {
    'zh-CN': '报告',
    'en-US': 'Report',
  },
  analysis_import_only_txt: {
    'zh-CN': '仅支持 .txt 文件导入',
    'en-US': 'Only .txt files are supported',
  },
  analysis_import_title: {
    'zh-CN': '导入 .txt 书籍',
    'en-US': 'Import .txt Book',
  },
  analysis_import_drag_hint: {
    'zh-CN': '拖拽到此处，或点击选择文件',
    'en-US': 'Drag & drop here, or click to choose file',
  },
  analysis_import_btn_pick: {
    'zh-CN': '选择文件',
    'en-US': 'Choose File',
  },
  analysis_import_success_prefix: {
    'zh-CN': '已导入《',
    'en-US': 'Imported "',
  },
  analysis_import_success_middle: {
    'zh-CN': '》 · ',
    'en-US': '" · ',
  },
  analysis_import_success_suffix: {
    'zh-CN': ' 章',
    'en-US': ' chapters',
  },
  analysis_sample_title: {
    'zh-CN': '内置示例语料',
    'en-US': 'Built-in Sample Corpus',
  },
  analysis_sample_subtitle: {
    'zh-CN': '（新手试手，一键导入）',
    'en-US': '(Beginner trial, one-click import)',
  },
  analysis_sample_help_title: {
    'zh-CN': '查看导入与拆书指南',
    'en-US': 'View Import & Deconstruction Guide',
  },
  analysis_prog_title: {
    'zh-CN': '分析进度',
    'en-US': 'Analysis Progress',
  },
  analysis_prog_status_current: {
    'zh-CN': '当前状态',
    'en-US': 'Current Status',
  },
  analysis_prog_checkpoint: {
    'zh-CN': '断点',
    'en-US': 'Checkpoint',
  },
  analysis_status_pending: {
    'zh-CN': '等待',
    'en-US': 'Pending',
  },
  analysis_status_success: {
    'zh-CN': '成功',
    'en-US': 'Success',
  },
  analysis_status_failed: {
    'zh-CN': '失败',
    'en-US': 'Failed',
  },
  analysis_status_skipped: {
    'zh-CN': '跳过',
    'en-US': 'Skipped',
  },
  analysis_chap_not_imported: {
    'zh-CN': '尚未导入书籍',
    'en-US': 'No book imported yet',
  },
  analysis_chap_prefix: {
    'zh-CN': '第',
    'en-US': 'Ch.',
  },
  analysis_chap_suffix: {
    'zh-CN': '章',
    'en-US': '',
  },
  analysis_chap_status_failed: {
    'zh-CN': '失败',
    'en-US': 'Failed',
  },
  analysis_chap_status_done: {
    'zh-CN': '完成',
    'en-US': 'Done',
  },
  analysis_chap_status_partial: {
    'zh-CN': '部分',
    'en-US': 'Partial',
  },
  analysis_chap_status_pending: {
    'zh-CN': '待处理',
    'en-US': 'Pending',
  },
  analysis_detail_title: {
    'zh-CN': '分析结果',
    'en-US': 'Analysis Result',
  },
  analysis_detail_need_select: {
    'zh-CN': '请先选择章节查看分析结果',
    'en-US': 'Please select a chapter to view analysis results',
  },
  analysis_detail_batch_label: {
    'zh-CN': '批次',
    'en-US': 'Batch',
  },
  analysis_detail_refresh: {
    'zh-CN': '刷新',
    'en-US': 'Refresh',
  },
  analysis_detail_not_generated: {
    'zh-CN': '该批次尚未生成此 pass 的结果（请先运行分析）',
    'en-US': 'No pass results generated for this batch yet (please run analysis first)',
  },
  analysis_pass_structure: {
    'zh-CN': '结构拆解',
    'en-US': 'Structure Pass',
  },
  analysis_pass_character: {
    'zh-CN': '人物弧光',
    'en-US': 'Character Pass',
  },
  analysis_pass_style: {
    'zh-CN': '文风指纹',
    'en-US': 'Style Pass',
  },
  analysis_pass_commercial: {
    'zh-CN': '商业评估',
    'en-US': 'Commercial Pass',
  },
  help_title: {
    'zh-CN': '帮助中心',
    'en-US': 'Help Center',
  },
  help_subtitle: {
    'zh-CN': '术语解释、操作指南、工作流、常见问题——都在这里。',
    'en-US': 'Terminology, user guides, workflows, and FAQs — all in one place.',
  },
  help_tab_start: {
    'zh-CN': '新手上路',
    'en-US': 'Quick Start',
  },
  help_tab_glossary: {
    'zh-CN': '术语表',
    'en-US': 'Glossary',
  },
  help_tab_guides: {
    'zh-CN': '功能指南',
    'en-US': 'Feature Guides',
  },
  help_tab_faq: {
    'zh-CN': '常见问题',
    'en-US': 'FAQ',
  },
  help_start_eco_title: {
    'zh-CN': '生态全景：数据是怎么流动的',
    'en-US': 'Ecosystem Overview: How Data Flows',
  },
  help_start_eco_summary_1: {
    'zh-CN': '记住这个顺序：',
    'en-US': 'Remember the pipeline order: ',
  },
  help_start_eco_summary_highlight: {
    'zh-CN': '先拆书，再蒸馏，最后用资产辅助写作',
    'en-US': 'Analyze first, Distill next, and then power Assisted Writing with assets',
  },
  help_start_eco_summary_2: {
    'zh-CN': '。质检贯穿全程——写完一章用单章检查，完稿用全书QC。',
    'en-US': '. Quality check is continuous — inspect chapters as you write, and run full book QC on final manuscripts.',
  },
  help_start_workflows_title: {
    'zh-CN': '四个典型工作流',
    'en-US': 'Four Canonical Workflows',
  },
  help_glossary_search: {
    'zh-CN': '搜索术语…',
    'en-US': 'Search terms…',
  },
  help_cat_all: {
    'zh-CN': '全部',
    'en-US': 'All',
  },
  help_cat_concept: {
    'zh-CN': '概念',
    'en-US': 'Concepts',
  },
  help_cat_asset: {
    'zh-CN': '资产',
    'en-US': 'Assets',
  },
  help_cat_feature: {
    'zh-CN': '功能',
    'en-US': 'Features',
  },
  help_glossary_example_prefix: {
    'zh-CN': '举例：',
    'en-US': 'Example: ',
  },
  help_glossary_empty: {
    'zh-CN': '没有找到匹配的术语，换个关键词试试。',
    'en-US': 'No matching terms found. Try another search term.',
  },
  help_guides_subtitle: {
    'zh-CN': '每个功能模块的详细操作步骤。点击展开查看。',
    'en-US': 'Detailed walkthroughs for each module. Click to expand.',
  },
  help_guides_steps_header: {
    'zh-CN': '操作步骤',
    'en-US': 'Step-by-Step Instructions',
  },
  help_guides_tips_header: {
    'zh-CN': '💡 提示',
    'en-US': '💡 Tips',
  },
  help_guides_faq_header: {
    'zh-CN': '常见问题',
    'en-US': 'Frequently Asked Questions',
  },
  help_guides_q_prefix: {
    'zh-CN': 'Q：',
    'en-US': 'Q: ',
  },
  help_guides_a_prefix: {
    'zh-CN': 'A：',
    'en-US': 'A: ',
  },
  advanced_tab_distill: {
    'zh-CN': '蒸馏',
    'en-US': 'Distillation',
  },
  advanced_tab_batch: {
    'zh-CN': '批量状态',
    'en-US': 'Batch Status',
  },
  advanced_tab_edit: {
    'zh-CN': '资产编辑',
    'en-US': 'Asset Editor',
  },
  advanced_tab_platform: {
    'zh-CN': '平台适配',
    'en-US': 'Platform Adaptation',
  },
  distill_title: {
    'zh-CN': '题材蒸馏',
    'en-US': 'Genre Distillation',
  },
  distill_genre_label: {
    'zh-CN': '题材',
    'en-US': 'Genre',
  },
  distill_btn_execute: {
    'zh-CN': '执行蒸馏',
    'en-US': 'Execute Distillation',
  },
  distill_status_available: {
    'zh-CN': '可蒸馏书目：',
    'en-US': 'Available Books: ',
  },
  distill_status_books_unit: {
    'zh-CN': ' 本 — ',
    'en-US': ' books — ',
  },
  distill_status_existing: {
    'zh-CN': '已有蒸馏产物：',
    'en-US': 'Existing Distilled Assets: ',
  },
  distill_status_assets_unit: {
    'zh-CN': ' 个',
    'en-US': ' items',
  },
  distill_chip_ready: {
    'zh-CN': '可蒸馏',
    'en-US': 'Ready to Distill',
  },
  distill_chip_insufficient: {
    'zh-CN': '书目不足（需≥2本）',
    'en-US': 'Insufficient Books (>=2 required)',
  },
  distill_result_success: {
    'zh-CN': '蒸馏完成',
    'en-US': 'Distillation Complete',
  },
  distill_result_books_prefix: {
    'zh-CN': ' 本书目 · ',
    'en-US': ' books · ',
  },
  distill_result_outputs_suffix: {
    'zh-CN': ' 个产出',
    'en-US': ' outputs',
  },
  distill_section_books: {
    'zh-CN': '参与书目',
    'en-US': 'Participating Books',
  },
  distill_section_dims: {
    'zh-CN': '蒸馏维度',
    'en-US': 'Distillation Dimensions',
  },
  distill_section_files: {
    'zh-CN': '产出文件（已入库）',
    'en-US': 'Generated Files (Persisted)',
  },
  distill_btn_hide_raw: {
    'zh-CN': '收起原始 JSON',
    'en-US': 'Hide Raw JSON',
  },
  distill_btn_view_raw: {
    'zh-CN': '查看原始 JSON',
    'en-US': 'View Raw JSON',
  },
  batch_status_title: {
    'zh-CN': '批量拆书状态',
    'en-US': 'Batch Deconstruction Status',
  },
  batch_status_empty: {
    'zh-CN': '暂无拆书数据',
    'en-US': 'No deconstruction data yet',
  },
  batch_chip_has_assets: {
    'zh-CN': '已有资产',
    'en-US': 'Assets Present',
  },
  asset_edit_title: {
    'zh-CN': '资产编辑',
    'en-US': 'Asset Editor',
  },
  asset_edit_select_label: {
    'zh-CN': '选择资产',
    'en-US': 'Select Asset',
  },
  asset_edit_btn_load: {
    'zh-CN': '加载',
    'en-US': 'Load',
  },
  asset_edit_btn_save: {
    'zh-CN': '保存',
    'en-US': 'Save',
  },
  asset_edit_readonly_hint: {
    'zh-CN': '题材文风卡索引（prose_card_index）为只读寻址表，不在可编辑列表中，请在「资产库」中查看。',
    'en-US': 'Genre style card index (prose_card_index) is a read-only index table and not editable; view in Asset Library.',
  },
  asset_edit_chip_json_valid: {
    'zh-CN': '✓ JSON 合法',
    'en-US': '✓ Valid JSON',
  },
  asset_edit_chip_json_invalid: {
    'zh-CN': '✗ JSON 错误',
    'en-US': '✗ JSON Error',
  },
  asset_edit_chip_unsaved: {
    'zh-CN': '未保存修改',
    'en-US': 'Unsaved Changes',
  },
  asset_edit_json_empty: {
    'zh-CN': '内容为空',
    'en-US': 'Content is empty',
  },
  asset_edit_json_top_object: {
    'zh-CN': '顶层必须是 JSON 对象',
    'en-US': 'Top level must be a JSON object',
  },
  asset_edit_json_error_prefix: {
    'zh-CN': 'JSON 错误：',
    'en-US': 'JSON Error: ',
  },
  asset_edit_json_valid: {
    'zh-CN': 'JSON 合法',
    'en-US': 'Valid JSON',
  },
  asset_edit_save_success: {
    'zh-CN': '保存成功',
    'en-US': 'Saved successfully',
  },
  asset_edit_content_label: {
    'zh-CN': '资产 JSON 内容',
    'en-US': 'Asset JSON Content',
  },
  system_tab_status: {
    'zh-CN': '系统状态',
    'en-US': 'System Status',
  },
  system_tab_compliance: {
    'zh-CN': '版权合规',
    'en-US': 'Copyright Compliance',
  },
  system_tab_models: {
    'zh-CN': '模型配置',
    'en-US': 'Model Config',
  },
  system_tab_settings: {
    'zh-CN': '设置',
    'en-US': 'Settings',
  },
  system_status_title: {
    'zh-CN': '系统状态',
    'en-US': 'System Status',
  },
  system_status_refresh: {
    'zh-CN': '刷新',
    'en-US': 'Refresh',
  },
  system_disk_title: {
    'zh-CN': '磁盘占用',
    'en-US': 'Disk Usage',
  },
  system_disk_assets: {
    'zh-CN': '资产：',
    'en-US': 'Assets: ',
  },
  system_disk_reports: {
    'zh-CN': '报告：',
    'en-US': 'Reports: ',
  },
  system_disk_corpus: {
    'zh-CN': '语料：',
    'en-US': 'Corpus: ',
  },
  system_disk_novel: {
    'zh-CN': '写作：',
    'en-US': 'Writing: ',
  },
  system_disk_db: {
    'zh-CN': '数据库：',
    'en-US': 'Database: ',
  },
  system_disk_total: {
    'zh-CN': '总计：',
    'en-US': 'Total: ',
  },
  system_counts_title: {
    'zh-CN': '数据统计',
    'en-US': 'Data Statistics',
  },
  system_counts_assets_prefix: {
    'zh-CN': '资产 ',
    'en-US': 'Assets: ',
  },
  system_counts_assets_unit: {
    'zh-CN': ' 个 | 报告 ',
    'en-US': ' | Reports: ',
  },
  system_counts_reports_unit: {
    'zh-CN': ' 份 | 已拆书 ',
    'en-US': ' | Analyzed Books: ',
  },
  system_counts_books_unit: {
    'zh-CN': ' 本',
    'en-US': ' books',
  },
  system_model_title: {
    'zh-CN': '模型状态',
    'en-US': 'Model Status',
  },
  system_model_configured: {
    'zh-CN': '已配置',
    'en-US': 'Configured',
  },
  system_model_unconfigured: {
    'zh-CN': '未配置',
    'en-US': 'Unconfigured',
  },
  system_paths_title: {
    'zh-CN': '路径',
    'en-US': 'Paths',
  },
  system_comp_title: {
    'zh-CN': '版权合规扫描',
    'en-US': 'Copyright Compliance Scan',
  },
  system_comp_btn_scan: {
    'zh-CN': '全量扫描',
    'en-US': 'Full Scan',
  },
  system_comp_summary_total: {
    'zh-CN': '共 ',
    'en-US': 'Total ',
  },
  system_comp_summary_assets: {
    'zh-CN': ' 个资产：',
    'en-US': ' assets: ',
  },
  system_settings_title: {
    'zh-CN': '系统设置',
    'en-US': 'System Settings',
  },
  system_settings_service: {
    'zh-CN': '服务',
    'en-US': 'Services',
  },
  system_settings_port: {
    'zh-CN': '端口：',
    'en-US': 'Port: ',
  },
  system_settings_batch_size: {
    'zh-CN': '批次大小：',
    'en-US': 'Batch Size: ',
  },
  system_settings_chars_unit: {
    'zh-CN': ' 字符',
    'en-US': ' chars',
  },
  system_settings_env_title: {
    'zh-CN': '环境变量覆盖',
    'en-US': 'Environment Overrides',
  },
  system_settings_env_unset: {
    'zh-CN': '（未设置）',
    'en-US': '(Not set)',
  },
  system_settings_notice: {
    'zh-CN': '设置修改请通过环境变量或直接编辑 gui/config.py。GUI 写入设置属阶段三规划。',
    'en-US': 'To modify settings, use environment variables or edit gui/config.py directly. GUI writing is planned for Phase 3.',
  },
  model_mgr_title: {
    'zh-CN': '模型管理',
    'en-US': 'Model Management',
  },
  model_mgr_add_btn: {
    'zh-CN': '添加模型',
    'en-US': 'Add Model',
  },
  model_mgr_empty_hint: {
    'zh-CN': '暂无模型配置，点击「添加模型」开始',
    'en-US': 'No model configured yet, click "Add Model" to begin',
  },
  model_mgr_chip_key_set: {
    'zh-CN': '已配 Key',
    'en-US': 'Key Set',
  },
  model_mgr_role_prefix: {
    'zh-CN': '角色：',
    'en-US': 'Roles: ',
  },
  model_mgr_btn_test: {
    'zh-CN': '测试',
    'en-US': 'Test',
  },
  model_mgr_btn_testing: {
    'zh-CN': '测试中',
    'en-US': 'Testing...',
  },
  model_mgr_btn_key: {
    'zh-CN': '密钥',
    'en-US': 'API Key',
  },
  model_mgr_btn_edit: {
    'zh-CN': '编辑',
    'en-US': 'Edit',
  },
  model_mgr_btn_delete: {
    'zh-CN': '删除',
    'en-US': 'Delete',
  },
  model_mgr_dialog_edit_prefix: {
    'zh-CN': '编辑模型: ',
    'en-US': 'Edit Model: ',
  },
  model_mgr_dialog_add: {
    'zh-CN': '添加模型',
    'en-US': 'Add Model',
  },
  model_mgr_quick_preset: {
    'zh-CN': '快速选择预设：',
    'en-US': 'Quick Presets: ',
  },
  model_mgr_field_id: {
    'zh-CN': '模型 ID',
    'en-US': 'Model ID',
  },
  model_mgr_field_id_helper: {
    'zh-CN': '唯一标识，如 my-gpt4',
    'en-US': 'Unique identifier, e.g. my-gpt4',
  },
  model_mgr_field_label: {
    'zh-CN': '显示名称',
    'en-US': 'Display Name',
  },
  model_mgr_field_protocol: {
    'zh-CN': '协议',
    'en-US': 'Protocol',
  },
  model_mgr_proto_openai: {
    'zh-CN': 'OpenAI 兼容',
    'en-US': 'OpenAI Compatible',
  },
  model_mgr_proto_anthropic: {
    'zh-CN': 'Anthropic',
    'en-US': 'Anthropic',
  },
  model_mgr_proto_ollama: {
    'zh-CN': 'Ollama',
    'en-US': 'Ollama',
  },
  model_mgr_field_base_url: {
    'zh-CN': 'Base URL',
    'en-US': 'Base URL',
  },
  model_mgr_field_base_url_helper: {
    'zh-CN': '如 https://api.openai.com/v1',
    'en-US': 'e.g. https://api.openai.com/v1',
  },
  model_mgr_field_name: {
    'zh-CN': '模型名称',
    'en-US': 'Model Name',
  },
  model_mgr_field_name_helper: {
    'zh-CN': '如 gpt-4o, claude-3-5-sonnet',
    'en-US': 'e.g. gpt-4o, claude-3-5-sonnet',
  },
  model_mgr_field_note: {
    'zh-CN': '备注',
    'en-US': 'Notes',
  },
  model_mgr_btn_cancel: {
    'zh-CN': '取消',
    'en-US': 'Cancel',
  },
  model_mgr_btn_save: {
    'zh-CN': '保存',
    'en-US': 'Save',
  },
  model_mgr_btn_add: {
    'zh-CN': '添加',
    'en-US': 'Add',
  },
  model_mgr_key_dialog_title: {
    'zh-CN': '设置 API Key: ',
    'en-US': 'Set API Key: ',
  },
  model_mgr_key_field: {
    'zh-CN': 'API Key',
    'en-US': 'API Key',
  },
  model_mgr_key_helper: {
    'zh-CN': 'Key 将加密存储在本地 .secrets.json',
    'en-US': 'Key will be encrypted and stored locally in .secrets.json',
  },
  model_mgr_msg_updated: {
    'zh-CN': '模型已更新',
    'en-US': 'Model updated',
  },
  model_mgr_msg_added: {
    'zh-CN': '模型已添加',
    'en-US': 'Model added',
  },
  model_mgr_confirm_delete: {
    'zh-CN': '确认删除模型 ',
    'en-US': 'Confirm deletion of model ',
  },
  model_mgr_msg_deleted: {
    'zh-CN': ' 已删除',
    'en-US': ' deleted',
  },
  model_mgr_msg_key_saved: {
    'zh-CN': 'API Key 已保存',
    'en-US': 'API Key saved',
  },
  model_mgr_msg_test_ok: {
    'zh-CN': ' 连接成功',
    'en-US': ' connected successfully',
  },
  model_mgr_msg_test_fail: {
    'zh-CN': ' 连接失败: ',
    'en-US': ' connection failed: ',
  },

  // 设置工作台 (SettingsWorkbench)
  settings_title: {
    'zh-CN': '系统设置',
    'en-US': 'System Settings',
  },
  settings_section_thresholds: {
    'zh-CN': '打分阈值',
    'en-US': 'Scoring Thresholds',
  },
  settings_section_writing: {
    'zh-CN': '写作设置',
    'en-US': 'Writing Settings',
  },
  settings_section_service: {
    'zh-CN': '服务配置',
    'en-US': 'Service Configuration',
  },
  settings_chip_restart: {
    'zh-CN': '需重启生效',
    'en-US': 'Restart Required',
  },
  settings_port_prefix: {
    'zh-CN': '端口：',
    'en-US': 'Port: ',
  },
  settings_batch_size_prefix: {
    'zh-CN': '批次大小：',
    'en-US': 'Batch Size: ',
  },
  settings_chars_unit: {
    'zh-CN': ' 字符',
    'en-US': ' chars',
  },
  settings_env_hint: {
    'zh-CN': '修改端口/批次大小请通过环境变量 NOVEL_LAB_GUI_PORT / NOVEL_LAB_GUI_BATCH_SIZE',
    'en-US': 'To modify port/batch size, use environment variables NOVEL_LAB_GUI_PORT / NOVEL_LAB_GUI_BATCH_SIZE',
  },
  settings_section_paths: {
    'zh-CN': '路径',
    'en-US': 'Paths',
  },
  settings_section_env: {
    'zh-CN': '环境变量覆盖',
    'en-US': 'Environment Overrides',
  },
  settings_env_unset: {
    'zh-CN': '（未设置）',
    'en-US': '(Not set)',
  },
  settings_btn_save: {
    'zh-CN': '保存设置',
    'en-US': 'Save Settings',
  },
  settings_btn_reset: {
    'zh-CN': '重置为默认',
    'en-US': 'Reset to Defaults',
  },
  settings_msg_saved: {
    'zh-CN': '设置已保存',
    'en-US': 'Settings saved successfully',
  },
  settings_msg_reset: {
    'zh-CN': '已重置为默认值',
    'en-US': 'Reset to default values successfully',
  },
  settings_confirm_reset: {
    'zh-CN': '确定将所有设置重置为默认值吗？此操作不可恢复。',
    'en-US': 'Are you sure you want to reset all settings to default values? This operation cannot be undone.',
  },
  settings_field_consistency_target: {
    'zh-CN': '一致性目标分',
    'en-US': 'Consistency Target',
  },
  settings_field_quality_pass_line: {
    'zh-CN': '质量及格线',
    'en-US': 'Quality Pass Line',
  },
  settings_field_quality_warn_line: {
    'zh-CN': '质量警告线',
    'en-US': 'Quality Warn Line',
  },
  settings_field_default_words: {
    'zh-CN': '默认字数',
    'en-US': 'Default Words',
  },
  settings_field_max_attempts: {
    'zh-CN': '最大改写轮数',
    'en-US': 'Max Rewrite Attempts',
  },
  settings_helper_consistency_target: {
    'zh-CN': '写作改写循环的一致性达标线（0-100）',
    'en-US': 'Consistency threshold for writing rewrite loop (0-100)',
  },
  settings_helper_quality_pass_line: {
    'zh-CN': '章节质量 PASS 阈值（默认 75）',
    'en-US': 'Chapter quality PASS threshold (default 75)',
  },
  settings_helper_quality_warn_line: {
    'zh-CN': '章节质量 WARN 阈值（默认 60）',
    'en-US': 'Chapter quality WARN threshold (default 60)',
  },
  settings_helper_default_words: {
    'zh-CN': '每章默认目标字数（100-20000）',
    'en-US': 'Default target words per chapter (100-20000)',
  },
  settings_helper_max_attempts: {
    'zh-CN': '1 初稿 + N-1 次改写（1-10）',
    'en-US': '1 first draft + N-1 rewrites (1-10)',
  },
  settings_err_required: {
    'zh-CN': '不能为空',
    'en-US': 'Cannot be empty',
  },
  settings_err_nan: {
    'zh-CN': '请输入数字',
    'en-US': 'Please enter a number',
  },
  settings_err_integer: {
    'zh-CN': '必须为整数',
    'en-US': 'Must be an integer',
  },
  settings_err_range_100: {
    'zh-CN': '必须在 0-100 之间',
    'en-US': 'Must be between 0 and 100',
  },
  settings_err_range_words: {
    'zh-CN': '必须在 100-20000 之间',
    'en-US': 'Must be between 100 and 20000',
  },
  settings_err_range_attempts: {
    'zh-CN': '必须在 1-10 之间',
    'en-US': 'Must be between 1 and 10',
  },
  settings_err_pass_gte_warn: {
    'zh-CN': '及格线必须 ≥ 警告线',
    'en-US': 'Pass line must be ≥ warn line',
  },
  settings_err_warn_lte_pass: {
    'zh-CN': '警告线必须 ≤ 及格线',
    'en-US': 'Warn line must be ≤ pass line',
  },

  settings_section_ui_mode: {
    'zh-CN': '界面偏好',
    'en-US': 'Interface Preference',
  },
  settings_ui_mode_desc: {
    'zh-CN': '简洁模式只显示核心功能（首页/分析/写作/质检），进阶模式显示全部工具。切换立即生效并自动保存。',
    'en-US': 'Simple shows core features (Home/Analysis/Writing/Quality); Advanced shows all tools. Switch takes effect immediately.',
  },
  settings_ui_mode_simple: {
    'zh-CN': '简洁',
    'en-US': 'Simple',
  },
  settings_ui_mode_advanced: {
    'zh-CN': '进阶',
    'en-US': 'Advanced',
  },
  settings_ui_mode_aria: {
    'zh-CN': '界面模式',
    'en-US': 'UI Mode',
  },
  ui_mode_simple: {
    'zh-CN': '简洁',
    'en-US': 'Simple',
  },
  ui_mode_advanced: {
    'zh-CN': '进阶',
    'en-US': 'Advanced',
  },
  ui_mode_tooltip_simple: {
    'zh-CN': '简洁模式：只显示核心功能，点击切换为进阶',
    'en-US': 'Simple mode: core features only. Click to switch to Advanced',
  },
  ui_mode_tooltip_advanced: {
    'zh-CN': '进阶模式：显示全部工具，点击切换为简洁',
    'en-US': 'Advanced mode: all tools visible. Click to switch to Simple',
  },
  // ==========================================
  // 管理后台 (AdminWorkbench)
  // ==========================================
  admin_title: {
    'zh-CN': '管理后台',
    'en-US': 'Admin Console',
  },
  admin_subtitle: {
    'zh-CN': 'ADMIN CONSOLE',
    'en-US': 'ADMIN CONSOLE',
  },
  admin_login_notice: {
    'zh-CN': '后台管理仅限本机访问。首次启动的初始密码见数据目录下的 admin-初始密码.txt（改密后自动删除）。',
    'en-US': 'Console access is restricted to localhost. Initial password for first launch is in admin-初始密码.txt (auto-deleted after change).',
  },
  admin_username: {
    'zh-CN': '用户名',
    'en-US': 'Username',
  },
  admin_password: {
    'zh-CN': '密码',
    'en-US': 'Password',
  },
  admin_login_btn: {
    'zh-CN': '登 录',
    'en-US': 'Sign In',
  },
  admin_logging_in: {
    'zh-CN': '登录中…',
    'en-US': 'Signing In…',
  },
  admin_force_change_notice: {
    'zh-CN': '首次登录请立即修改初始密码，修改完成前其他功能不可用。',
    'en-US': 'Please change initial password immediately upon first login. Other features are locked until updated.',
  },
  admin_tab_dashboard: {
    'zh-CN': '仪表盘',
    'en-US': 'Dashboard',
  },
  admin_tab_books: {
    'zh-CN': '书库管理',
    'en-US': 'Books',
  },
  admin_tab_assets: {
    'zh-CN': '资产管理',
    'en-US': 'Assets',
  },
  admin_tab_audit: {
    'zh-CN': '操作日志',
    'en-US': 'Audit Logs',
  },
  admin_tab_sessions: {
    'zh-CN': '会话管理',
    'en-US': 'Sessions',
  },
  admin_tab_security: {
    'zh-CN': '安全设置',
    'en-US': 'Security',
  },
  admin_logout: {
    'zh-CN': '退出',
    'en-US': 'Logout',
  },
  admin_refresh: {
    'zh-CN': '刷新',
    'en-US': 'Refresh',
  },
  admin_help_guide: {
    'zh-CN': '查看管理后台指南',
    'en-US': 'View Admin Console Guide',
  },

  // 仪表盘
  admin_dash_title: {
    'zh-CN': '系统仪表盘',
    'en-US': 'System Dashboard',
  },
  admin_dash_books: {
    'zh-CN': '书籍',
    'en-US': 'Books',
  },
  admin_dash_analyzing: {
    'zh-CN': '本分析中',
    'en-US': 'analyzing',
  },
  admin_dash_idle: {
    'zh-CN': '全部空闲',
    'en-US': 'All idle',
  },
  admin_dash_assets: {
    'zh-CN': '资产',
    'en-US': 'Assets',
  },
  admin_dash_reports: {
    'zh-CN': '报告',
    'en-US': 'Reports',
  },
  admin_dash_reports_sub: {
    'zh-CN': '拆书/笔法报告',
    'en-US': 'Deconstruction & Style Reports',
  },
  admin_dash_disk_usage: {
    'zh-CN': '数据占用',
    'en-US': 'Disk Usage',
  },
  admin_dash_uptime: {
    'zh-CN': '运行',
    'en-US': 'Uptime',
  },
  admin_dash_disk_breakdown: {
    'zh-CN': '磁盘占用',
    'en-US': 'Disk Breakdown',
  },
  admin_dash_recent_books: {
    'zh-CN': '最近书籍',
    'en-US': 'Recent Books',
  },
  admin_dash_chapters_suffix: {
    'zh-CN': '章',
    'en-US': 'chs',
  },
  admin_dash_recent_ops: {
    'zh-CN': '最近操作',
    'en-US': 'Recent Operations',
  },

  // 书库管理
  admin_books_title: {
    'zh-CN': '书库管理',
    'en-US': 'Book Management',
  },
  admin_books_count_suffix: {
    'zh-CN': '本',
    'en-US': 'books',
  },
  admin_col_book_title: {
    'zh-CN': '书名',
    'en-US': 'Title',
  },
  admin_col_chapters: {
    'zh-CN': '章节',
    'en-US': 'Chapters',
  },
  admin_col_status: {
    'zh-CN': '状态',
    'en-US': 'Status',
  },
  admin_col_actions: {
    'zh-CN': '操作',
    'en-US': 'Actions',
  },
  admin_books_delete_btn: {
    'zh-CN': '删除',
    'en-US': 'Delete',
  },
  admin_books_delete_analyzing_tip: {
    'zh-CN': '分析中的书籍不可删除',
    'en-US': 'Books being analyzed cannot be deleted',
  },
  admin_books_delete_tip: {
    'zh-CN': '删除本书全部数据',
    'en-US': 'Delete all data for this book',
  },
  admin_books_empty: {
    'zh-CN': '暂无书籍',
    'en-US': 'No books available',
  },
  admin_books_dialog_title: {
    'zh-CN': '确认删除',
    'en-US': 'Confirm Deletion',
  },
  admin_books_dialog_desc: {
    'zh-CN': '将彻底删除《{title}》的状态文件、原文、分析资产与数据库记录，此操作不可恢复。继续吗？',
    'en-US': 'Permanently delete all state files, manuscripts, analytical assets, and database records for "{title}". This operation cannot be undone. Continue?',
  },
  admin_cancel: {
    'zh-CN': '取消',
    'en-US': 'Cancel',
  },
  admin_confirm_delete: {
    'zh-CN': '确认删除',
    'en-US': 'Confirm Delete',
  },
  admin_deleting: {
    'zh-CN': '删除中…',
    'en-US': 'Deleting…',
  },
  admin_books_partial_delete: {
    'zh-CN': '《{title}》删除不完全，残留需手动清理：{warnings}',
    'en-US': '"{title}" was partially deleted. Manual cleanup required: {warnings}',
  },
  admin_books_delete_success: {
    'zh-CN': '已删除《{title}》，清理：{removed}',
    'en-US': 'Deleted "{title}", cleaned: {removed}',
  },

  // 资产管理
  admin_assets_title: {
    'zh-CN': '资产管理',
    'en-US': 'Asset Management',
  },
  admin_assets_kind_all: {
    'zh-CN': '全部',
    'en-US': 'All',
  },
  admin_assets_kind_voice_card: {
    'zh-CN': '笔法卡',
    'en-US': 'Voice Cards',
  },
  admin_assets_kind_genre_pack: {
    'zh-CN': '题材包',
    'en-US': 'Genre Packs',
  },
  admin_assets_kind_genre_prose_card: {
    'zh-CN': '笔法卡片',
    'en-US': 'Prose Cards',
  },
  admin_assets_kind_report: {
    'zh-CN': '报告',
    'en-US': 'Reports',
  },
  admin_assets_filter_kind: {
    'zh-CN': '类型',
    'en-US': 'Type',
  },
  admin_col_name: {
    'zh-CN': '名称',
    'en-US': 'Name',
  },
  admin_col_kind: {
    'zh-CN': '类型',
    'en-US': 'Kind',
  },
  admin_assets_delete_confirm: {
    'zh-CN': '删除资产「{name}」？（将移入回收站）',
    'en-US': 'Delete asset "{name}"? (Moved to recycle bin)',
  },
  admin_assets_delete_success: {
    'zh-CN': '已删除资产「{name}」',
    'en-US': 'Deleted asset "{name}"',
  },
  admin_assets_empty: {
    'zh-CN': '暂无资产',
    'en-US': 'No assets available',
  },

  // 操作日志
  admin_audit_title: {
    'zh-CN': '操作日志（最近 200 条）',
    'en-US': 'Audit Logs (Recent 200)',
  },
  admin_audit_filter_action: {
    'zh-CN': '按动作过滤',
    'en-US': 'Filter by Action',
  },
  admin_audit_filter_action_ph: {
    'zh-CN': '如 admin.login',
    'en-US': 'e.g. admin.login',
  },
  admin_audit_filter_user: {
    'zh-CN': '按用户过滤',
    'en-US': 'Filter by User',
  },
  admin_audit_filter_user_ph: {
    'zh-CN': '如 admin',
    'en-US': 'e.g. admin',
  },
  admin_audit_filter_btn: {
    'zh-CN': '筛选',
    'en-US': 'Filter',
  },
  admin_audit_clear_btn: {
    'zh-CN': '清除',
    'en-US': 'Clear',
  },
  admin_col_time: {
    'zh-CN': '时间',
    'en-US': 'Time',
  },
  admin_col_user: {
    'zh-CN': '用户',
    'en-US': 'User',
  },
  admin_col_ip: {
    'zh-CN': 'IP',
    'en-US': 'IP',
  },
  admin_col_action: {
    'zh-CN': '动作',
    'en-US': 'Action',
  },
  admin_col_detail: {
    'zh-CN': '详情',
    'en-US': 'Detail',
  },
  admin_audit_empty: {
    'zh-CN': '暂无日志',
    'en-US': 'No audit logs',
  },

  // 会话管理
  admin_sessions_title: {
    'zh-CN': '在线会话',
    'en-US': 'Active Sessions',
  },
  admin_sessions_revoke_current_confirm: {
    'zh-CN': '这是你当前正在使用的会话！吊销后你将立即被登出。确定继续吗？',
    'en-US': 'This is your current active session! You will be logged out immediately upon revoking. Continue?',
  },
  admin_sessions_revoke_confirm: {
    'zh-CN': '确定吊销会话 {id}？该会话将立即失效。',
    'en-US': 'Revoke session {id}? It will be invalidated immediately.',
  },
  admin_col_session_id: {
    'zh-CN': '会话 ID（前缀）',
    'en-US': 'Session ID (Prefix)',
  },
  admin_col_created_at: {
    'zh-CN': '创建时间',
    'en-US': 'Created At',
  },
  admin_col_expires_at: {
    'zh-CN': '过期时间',
    'en-US': 'Expires At',
  },
  admin_session_current: {
    'zh-CN': '当前',
    'en-US': 'Current',
  },
  admin_session_revoke_btn: {
    'zh-CN': '吊销',
    'en-US': 'Revoke',
  },
  admin_sessions_empty: {
    'zh-CN': '无在线会话',
    'en-US': 'No active sessions',
  },

  // 安全设置
  admin_sec_title: {
    'zh-CN': '修改密码',
    'en-US': 'Change Password',
  },
  admin_sec_subtitle: {
    'zh-CN': '修改后所有已登录会话立即失效，需要重新登录。',
    'en-US': 'All active sessions will be invalidated upon change, requiring re-login.',
  },
  admin_sec_mismatch: {
    'zh-CN': '两次输入的新密码不一致',
    'en-US': 'New passwords do not match',
  },
  admin_sec_min_length: {
    'zh-CN': '新密码至少 8 位',
    'en-US': 'New password must be at least 8 characters',
  },
  admin_sec_success: {
    'zh-CN': '密码已修改，历史会话已吊销，请重新登录。',
    'en-US': 'Password changed successfully. Existing sessions revoked, please sign in again.',
  },
  admin_sec_old_pw: {
    'zh-CN': '原密码',
    'en-US': 'Current Password',
  },
  admin_sec_new_pw: {
    'zh-CN': '新密码（至少 8 位）',
    'en-US': 'New Password (at least 8 chars)',
  },
  admin_sec_confirm_pw: {
    'zh-CN': '确认新密码',
    'en-US': 'Confirm New Password',
  },
  admin_sec_submit_btn: {
    'zh-CN': '修改密码',
    'en-US': 'Change Password',
  },
  admin_sec_submitting: {
    'zh-CN': '提交中…',
    'en-US': 'Submitting…',
  },
  admin_sec_specs_title: {
    'zh-CN': '安全说明',
    'en-US': 'Security Specifications',
  },
  admin_sec_specs_item1: {
    'zh-CN': '· 密码经 PBKDF2-HMAC-SHA256（20 万轮）加盐哈希存储，服务端不保存明文',
    'en-US': '· Password stored with PBKDF2-HMAC-SHA256 (200k rounds) salted hash, plaintext never stored',
  },
  admin_sec_specs_item2: {
    'zh-CN': '· 会话 Cookie 为 HttpOnly，有效期 12 小时',
    'en-US': '· Session cookie is HttpOnly with 12-hour expiration',
  },
  admin_sec_specs_item3: {
    'zh-CN': '· 连续 5 次登录失败将锁定 IP 5 分钟',
    'en-US': '· 5 consecutive failed logins lock IP for 5 minutes',
  },
  admin_sec_specs_item4: {
    'zh-CN': '· 所有管理操作记入审计日志',
    'en-US': '· All administrative operations recorded in audit log',
  },
  admin_uptime_hours_mins: {
    'zh-CN': '{h} 小时 {m} 分',
    'en-US': '{h}h {m}m',
  },
  admin_uptime_mins: {
    'zh-CN': '{m} 分钟',
    'en-US': '{m} mins',
  },

  // ==========================================
  // 命令面板 (CommandPalette)
  // ==========================================
  cmd_search_placeholder: {
    'zh-CN': '搜索工作台或操作…',
    'en-US': 'Search workbenches or actions…',
  },
  cmd_empty: {
    'zh-CN': '没有匹配的结果',
    'en-US': 'No matching results',
  },
  cmd_group_workbench: {
    'zh-CN': '工作台',
    'en-US': 'Workbenches',
  },
  cmd_group_actions: {
    'zh-CN': '操作',
    'en-US': 'Actions',
  },
  cmd_goto_prefix: {
    'zh-CN': '前往',
    'en-US': 'Go to ',
  },
  cmd_nav_home: {
    'zh-CN': '首页',
    'en-US': 'Home',
  },
  cmd_nav_analysis: {
    'zh-CN': '分析拆书',
    'en-US': 'Book Analysis',
  },
  cmd_nav_writing: {
    'zh-CN': '辅助写作 (沉浸创作室与工坊)',
    'en-US': 'Writing Studio & Workbenches',
  },
  cmd_nav_quality: {
    'zh-CN': '质量检验',
    'en-US': 'Quality Check',
  },
  cmd_nav_assets: {
    'zh-CN': '资产库',
    'en-US': 'Asset Library',
  },
  cmd_nav_advanced: {
    'zh-CN': '高级功能',
    'en-US': 'Advanced Features',
  },
  cmd_nav_system: {
    'zh-CN': '系统',
    'en-US': 'System',
  },
  cmd_nav_settings: {
    'zh-CN': '设置',
    'en-US': 'Settings',
  },
  cmd_nav_admin: {
    'zh-CN': '管理后台',
    'en-US': 'Admin Console',
  },
  cmd_nav_help: {
    'zh-CN': '帮助中心',
    'en-US': 'Help Center',
  },
  cmd_theme_dark: {
    'zh-CN': '切换为暗色模式',
    'en-US': 'Switch to Dark Mode',
  },
  cmd_theme_light: {
    'zh-CN': '切换为亮色模式',
    'en-US': 'Switch to Light Mode',
  },
  cmd_shortcut_nav: {
    'zh-CN': '↑↓ 导航',
    'en-US': '↑↓ Navigate',
  },
  cmd_shortcut_select: {
    'zh-CN': '↵ 选择',
    'en-US': '↵ Select',
  },
  cmd_shortcut_close: {
    'zh-CN': 'esc 关闭',
    'en-US': 'esc Close',
  },
  cmd_search_btn: {
    'zh-CN': '搜索…',
    'en-US': 'Search…',
  },

  cmd_group_creation: { 'zh-CN': '创作', 'en-US': 'Creation' },
  cmd_group_assets: { 'zh-CN': '资产', 'en-US': 'Assets' },
  cmd_group_system: { 'zh-CN': '系统', 'en-US': 'System' },
  cmd_creation_new_project: { 'zh-CN': '新建项目', 'en-US': 'New Project' },
  cmd_creation_new_outline: { 'zh-CN': '新建大纲', 'en-US': 'New Outline' },
  cmd_creation_new_character: { 'zh-CN': '新建人物', 'en-US': 'New Character' },
  cmd_creation_go_studio: { 'zh-CN': '去写作 — 沉浸创作室', 'en-US': 'Go to Studio (Writing)' },
  cmd_creation_go_pipeline: { 'zh-CN': '去写作 — 工坊流水线', 'en-US': 'Go to Pipeline (Writing)' },
  cmd_creation_go_analysis: { 'zh-CN': '去拆书', 'en-US': 'Go to Analysis' },
  cmd_creation_view_results: { 'zh-CN': '查看分析结果', 'en-US': 'View Analysis Results' },
  cmd_asset_voice: { 'zh-CN': '查看声线卡', 'en-US': 'View Voice Cards' },
  cmd_asset_genre_pack: { 'zh-CN': '查看题材包', 'en-US': 'View Genre Packs' },
  cmd_asset_distilled: { 'zh-CN': '查看蒸馏规则', 'en-US': 'View Distilled Rules' },
  cmd_asset_prose_card: { 'zh-CN': '查看文风卡', 'en-US': 'View Style Cards' },
  cmd_asset_craft: { 'zh-CN': '查看笔法卡', 'en-US': 'View Craft Cards' },
  cmd_asset_trope: { 'zh-CN': '查看桥段库', 'en-US': 'View Trope Library' },
  cmd_asset_report: { 'zh-CN': '查看报告', 'en-US': 'View Reports' },
  cmd_system_config_model: { 'zh-CN': '配置模型', 'en-US': 'Configure Model' },
  cmd_system_uimode_simple: { 'zh-CN': '切换为简洁模式', 'en-US': 'Switch to Simple Mode' },
  cmd_system_uimode_advanced: { 'zh-CN': '切换为完整模式', 'en-US': 'Switch to Advanced Mode' },
  cmd_system_help_start: { 'zh-CN': '打开帮助 — 新手上路', 'en-US': 'Open Help — Getting Started' },
  cmd_system_help_glossary: { 'zh-CN': '打开帮助 — 术语表', 'en-US': 'Open Help — Glossary' },
  cmd_system_help_guides: { 'zh-CN': '打开帮助 — 功能指南', 'en-US': 'Open Help — Guides' },
  cmd_system_help_faq: { 'zh-CN': '打开帮助 — 常见问题', 'en-US': 'Open Help — FAQ' },


  // ==========================================
  // 写作注入 / 生成 表单标签（2026-11-02）
  // ==========================================
  gen_voice_label: {
    'zh-CN': '声线卡（必选）',
    'en-US': 'Voice Card (required)',
  },
  gen_genre_pack_label: {
    'zh-CN': '题材包（可选）',
    'en-US': 'Genre Pack (optional)',
  },
  gen_craft_label: {
    'zh-CN': '笔法卡（可选）',
    'en-US': 'Craft Card (optional)',
  },
  gen_task_label: {
    'zh-CN': '写作要点',
    'en-US': 'Writing Brief',
  },
  gen_none_option: {
    'zh-CN': '无',
    'en-US': 'None',
  },
  gen_genre_pack_hint: {
    'zh-CN': '题材包决定注入的结构与商业约束；与声线卡题材不一致时后端会拒绝',
    'en-US': 'The genre pack governs structure and commercial constraints; a mismatch with the voice card genre will be rejected',
  },


  gen_distilled_label: {
    'zh-CN': '蒸馏规则（可选）',
    'en-US': 'Distilled Rules (optional)',
  },
  gen_prose_card_label: {
    'zh-CN': '文风参照卡（可选）',
    'en-US': 'Style Reference Card (optional)',
  },
  gen_generate_prompt: {
    'zh-CN': '生成 Prompt',
    'en-US': 'Build Prompt',
  },
  gen_no_assets_hint: {
    'zh-CN': '暂无可用资产，请先在「分析」工作台完成拆书',
    'en-US': 'No assets available yet — run a book analysis first',
  },
  gen_genre_mismatch_prefix: {
    'zh-CN': '题材不一致（铁律一：禁止跨题材污染）：声线卡为「{voice}」，',
    'en-US': 'Genre mismatch (iron law 1 — no cross-genre mixing): voice card is "{voice}", ',
  },
  gen_genre_mismatch_suffix: {
    'zh-CN': '。提交会被后端拒绝（400），请换成同题材资产，或将题材未知的一侧留空。',
    'en-US': '. The backend will reject this (400). Pick same-genre assets, or leave the unknown side empty.',
  },
  gen_same_genre_tag: {
    'zh-CN': '（同题材）',
    'en-US': ' (same genre)',
  },
  gen_kind_genre_pack: {
    'zh-CN': '题材包',
    'en-US': 'Genre Pack',
  },
  gen_kind_craft: {
    'zh-CN': '笔法卡',
    'en-US': 'Craft Card',
  },
  gen_kind_distilled: {
    'zh-CN': '蒸馏规则',
    'en-US': 'Distilled Rules',
  },

  // ==========================================
  // 首启引导 (OnboardingWizard)
  // ==========================================
  onboarding_s1_title: {
    'zh-CN': '欢迎使用暮冬念春',
    'en-US': 'Welcome to Exoscribe',
  },
  onboarding_s1_body: {
    'zh-CN': '把优秀小说拆成可复用的写作资产，再用这些资产驱动创作。全流程在本机完成，不会上传任何数据。四步上手，随时可跳过。',
    'en-US': 'Deconstruct masterworks into reusable writing assets, then drive creative prose. 100% offline & local, never uploading data. 4 steps to start, skip anytime.',
  },
  onboarding_next: {
    'zh-CN': '下一步',
    'en-US': 'Next',
  },
  onboarding_s2_title: {
    'zh-CN': '第一步：导入并拆书',
    'en-US': 'Step 1: Import & Deconstruct',
  },
  onboarding_s2_body: {
    'zh-CN': '到「分析」页导入一本 TXT 全本，选择题材后启动拆书。拆解完成后自动生成文风卡、笔法卡、结构/商业观测等资产与万字分析报告。',
    'en-US': 'Go to "Analysis" to import a full TXT novel, select a genre, and start deconstruction. Automatically extracts voice cards, prose cards, structure/commercial metrics, and comprehensive reports.',
  },
  onboarding_goto_import: {
    'zh-CN': '去导入',
    'en-US': 'Go to Import',
  },
  onboarding_goto_model: {
    'zh-CN': '去配置模型',
    'en-US': 'Configure Model',
  },
  onboarding_s2_model_hint: {
    'zh-CN': '配好模型才能拆书，也可先用示例语料体验离线功能',
    'en-US': 'Configure a model to run deconstruction — or explore sample assets & offline tools first.',
  },
  onboarding_s3_title: {
    'zh-CN': '第二步：查看资产与质检',
    'en-US': 'Step 2: Inspect Assets & QC',
  },
  onboarding_s3_body: {
    'zh-CN': '「资产库」浏览全部结构化资产；「质检」页可对任意章节跑 12 维质量检查与全书质检；「写作」页用资产注入辅助生成新章节。',
    'en-US': 'Browse all structured assets in "Asset Library"; run 12-dimensional QC and full-book checks in "Quality"; generate chapters with asset injection in "Writing".',
  },
  onboarding_s4_title: {
    'zh-CN': '下一步做什么',
    'en-US': 'What next?',
  },
  onboarding_s4_body: {
    'zh-CN': '挑一个开始，边用边熟悉：',
    'en-US': 'Pick one to get started:',
  },
  onboarding_s4_action_analysis: {
    'zh-CN': '拆书',
    'en-US': 'Analyze a Book',
  },
  onboarding_s4_action_analysis_desc: {
    'zh-CN': '选一本 TXT 一键拆解',
    'en-US': 'Deconstruct a TXT novel',
  },
  onboarding_s4_action_assets: {
    'zh-CN': '逛资产库',
    'en-US': 'Browse Assets',
  },
  onboarding_s4_action_assets_desc: {
    'zh-CN': '看示例资产长什么样',
    'en-US': 'See what assets look like',
  },
  onboarding_s4_action_writing: {
    'zh-CN': '写一章',
    'en-US': 'Write a Chapter',
  },
  onboarding_s4_action_writing_desc: {
    'zh-CN': '用示例资产试写',
    'en-US': 'Try writing with sample assets',
  },
  onboarding_get_started: {
    'zh-CN': '开始使用',
    'en-US': 'Get Started',
  },
  onboarding_skip: {
    'zh-CN': '跳过',
    'en-US': 'Skip',
  },
  onboarding_prev: {
    'zh-CN': '上一步',
    'en-US': 'Back',
  },
  onboarding_replay: {
    'zh-CN': '重看引导',
    'en-US': 'Replay tour',
  },

  // ==========================================
  // 就地说明 (InlineGuide)
  // ==========================================
  inline_guide_collapse: {
    'zh-CN': '收起说明',
    'en-US': 'Collapse guide',
  },
  inline_guide_expand: {
    'zh-CN': '展开说明',
    'en-US': 'Expand guide',
  },
  inline_guide_example: {
    'zh-CN': '示例',
    'en-US': 'Example',
  },

  // ==========================================
  // 桥段灵感面板 (TropePanel)
  // ==========================================
  trope_title: {
    'zh-CN': '桥段库 · 找灵感',
    'en-US': 'Trope Library & Inspiration',
  },
  trope_count: {
    'zh-CN': '{n} 条',
    'en-US': '{n} tropes',
  },
  trope_subtitle: {
    'zh-CN': '灵感枯竭时翻一翻：选一条桥段，一键写入下面的「写作要点」。',
    'en-US': 'Browse when stuck: select a trope and click to insert into writing prompt.',
  },
  trope_category: {
    'zh-CN': '分类',
    'en-US': 'Category',
  },
  trope_cat_all: {
    'zh-CN': '全部',
    'en-US': 'All',
  },
  trope_search: {
    'zh-CN': '搜索桥段',
    'en-US': 'Search Tropes',
  },
  trope_search_ph: {
    'zh-CN': '关键词：名称 / 骨架 / 参数',
    'en-US': 'Keywords: name / skeleton / parameters',
  },
  trope_applicable_only: {
    'zh-CN': '只看当前题材适用（{g}）',
    'en-US': 'Only applicable to current genre ({g})',
  },
  trope_applicable_unrecognized: {
    'zh-CN': '只看当前题材适用（未识别到题材）',
    'en-US': 'Only applicable to current genre (unrecognized)',
  },
  trope_stat_filtered: {
    'zh-CN': '{filtered} / {total} 条',
    'en-US': '{filtered} / {total} tropes',
  },
  trope_empty: {
    'zh-CN': '没有符合筛选的桥段，换个分类或关键词试试。',
    'en-US': 'No matching tropes. Try another category or keyword.',
  },
  trope_select_hint: {
    'zh-CN': '点左侧任意桥段查看骨架（含铺垫→激化→引爆→余波四段式与可调参数）。',
    'en-US': 'Select any trope on the left to view skeleton (4 beats: setup, escalation, payoff, aftermath & parameters).',
  },
  trope_setup: {
    'zh-CN': '铺垫：',
    'en-US': 'Setup: ',
  },
  trope_escalation: {
    'zh-CN': '激化：',
    'en-US': 'Escalation: ',
  },
  trope_payoff: {
    'zh-CN': '引爆：',
    'en-US': 'Payoff: ',
  },
  trope_aftermath: {
    'zh-CN': '余波：',
    'en-US': 'Aftermath: ',
  },
  trope_parameters: {
    'zh-CN': '可调参数：',
    'en-US': 'Parameters: ',
  },
  trope_failures: {
    'zh-CN': '常见翻车：',
    'en-US': 'Common Pitfalls: ',
  },
  trope_btn_insert: {
    'zh-CN': '写入写作要点',
    'en-US': 'Insert into Prompt',
  },
  trope_btn_already: {
    'zh-CN': '已在写作要点中',
    'en-US': 'Already in Prompt',
  },
  trope_already_hint: {
    'zh-CN': '该桥段已写入写作要点，无需重复添加。',
    'en-US': 'This trope has already been inserted into prompt.',
  },

  // ==========================================
  // 文风面板 (StylePanel)
  // ==========================================
  style_tab_analyze: {
    'zh-CN': '风格分析',
    'en-US': 'Style Analysis',
  },
  style_tab_library: {
    'zh-CN': '风格库',
    'en-US': 'Style Library',
  },
  style_guide_what: {
    'zh-CN': '从一段样本文本里提取可量化的风格指标（句长、对话占比、情绪密度等），保存成风格卡，方便以后对照和复用。',
    'en-US': 'Extract quantifiable style metrics (sentence length, dialogue ratio, emotion density, etc.) from a text sample into a reusable style card.',
  },
  style_guide_s1: {
    'zh-CN': '起一个风格名称，如：悬疑冷峻风。',
    'en-US': 'Give it a style name, e.g. Suspenseful Gritty.',
  },
  style_guide_s2: {
    'zh-CN': '粘贴至少 100 字的代表性文本（最好是你认可的成品段落）。',
    'en-US': 'Paste at least 100 characters of representative text.',
  },
  style_guide_s3: {
    'zh-CN': '点「分析风格」，看平均句长、对话占比等指标。',
    'en-US': 'Click "Analyze Style" to inspect sentence length, dialogue ratio, and other metrics.',
  },
  style_guide_s4: {
    'zh-CN': '确认指标符合预期后点「保存风格卡」，它会出现在「风格库」里。',
    'en-US': 'Confirm metrics match expectations, then click "Save Style Card" to add to your library.',
  },
  style_guide_tip1: {
    'zh-CN': '样本越有代表性，风格卡越准；拼凑的多段文字会拉平均值。',
    'en-US': 'More representative samples yield sharper cards; stitched fragments dilute averages.',
  },
  style_name_label: {
    'zh-CN': '风格名称',
    'en-US': 'Style Name',
  },
  style_name_helper: {
    'zh-CN': '保存时使用，如：悬疑冷峻风',
    'en-US': 'Used for saving, e.g. Suspenseful Gritty',
  },
  style_text_label: {
    'zh-CN': '文本样本',
    'en-US': 'Text Sample',
  },
  style_text_helper: {
    'zh-CN': '粘贴至少 100 字的代表性文本',
    'en-US': 'Paste at least 100 characters of representative prose',
  },
  style_btn_analyze: {
    'zh-CN': '分析风格',
    'en-US': 'Analyze Style',
  },
  style_btn_analyzing: {
    'zh-CN': '分析中…',
    'en-US': 'Analyzing…',
  },
  style_metrics_title: {
    'zh-CN': '风格指标',
    'en-US': 'Style Metrics',
  },
  style_metric_avg_sentence: {
    'zh-CN': '平均句长：',
    'en-US': 'Avg Sentence Length: ',
  },
  style_metric_avg_sentence_unit: {
    'zh-CN': ' 字',
    'en-US': ' chars',
  },
  style_metric_dialogue_ratio: {
    'zh-CN': '对话占比：',
    'en-US': 'Dialogue Ratio: ',
  },
  style_metric_emotion_density: {
    'zh-CN': '情绪密度：',
    'en-US': 'Emotion Density: ',
  },
  style_metric_emotion_density_unit: {
    'zh-CN': '/千字',
    'en-US': ' /1k chars',
  },
  style_metric_avg_paragraph: {
    'zh-CN': '段落均长：',
    'en-US': 'Avg Paragraph Length: ',
  },
  style_metric_avg_paragraph_unit: {
    'zh-CN': ' 字',
    'en-US': ' chars',
  },
  style_metric_short_paragraph_ratio: {
    'zh-CN': '短段占比：',
    'en-US': 'Short Paragraph Ratio: ',
  },
  style_metric_total_chars: {
    'zh-CN': '总字数：',
    'en-US': 'Total Characters: ',
  },
  style_btn_save: {
    'zh-CN': '保存风格卡',
    'en-US': 'Save Style Card',
  },
  style_save_success: {
    'zh-CN': '风格「{name}」已保存',
    'en-US': 'Style "{name}" saved',
  },
  style_delete_confirm: {
    'zh-CN': '确定删除风格「{name}」吗？此操作不可恢复。',
    'en-US': 'Delete style "{name}"? This action cannot be undone.',
  },
  style_delete_success: {
    'zh-CN': '风格「{name}」已删除',
    'en-US': 'Style "{name}" deleted',
  },
  style_library_empty: {
    'zh-CN': '暂无风格卡，请先在「风格分析」中创建',
    'en-US': 'No style cards yet. Create one in "Style Analysis".',
  },
  style_lib_summary: {
    'zh-CN': '句长 {s} 字 | 对话 {d}%',
    'en-US': 'Sentence {s} chars | Dialogue {d}%',
  },

  // ==========================================
  // 阅读器 (ReaderPanel)
  // ==========================================
  reader_empty: {
    'zh-CN': '请在左侧选择章节开始阅读',
    'en-US': 'Please select a chapter on the left to start reading',
  },
  reader_prev_chapter: {
    'zh-CN': '上一章',
    'en-US': 'Previous Chapter',
  },
  reader_next_chapter: {
    'zh-CN': '下一章',
    'en-US': 'Next Chapter',
  },
  reader_chapter_title: {
    'zh-CN': '第{index}章 {title}',
    'en-US': 'Chapter {index}: {title}',
  },

  // ==========================================
  // 通用加载边界 (AsyncBoundary)
  // ==========================================
  async_empty_title: {
    'zh-CN': '暂无数据',
    'en-US': 'No Data Available',
  },
  async_retry_btn: {
    'zh-CN': '重试',
    'en-US': 'Retry',
  },

  // ==========================================
  // 错误边界 (ErrorBoundary)
  // ==========================================
  error_boundary_title: {
    'zh-CN': '组件加载失败',
    'en-US': 'Component Failed to Load',
  },
  error_boundary_unknown: {
    'zh-CN': '未知错误',
    'en-US': 'Unknown Error',
  },
  error_boundary_retry: {
    'zh-CN': '重试',
    'en-US': 'Retry',
  },

  // ==========================================
  // 通用操作 (Common Actions)
  // ==========================================
  action_delete: {
    'zh-CN': '删除',
    'en-US': 'Delete',
  },

  // ==========================================
  // QC 可视化图表 (QcVisuals)
  // ==========================================
  qc_vis_overview_title: {
    'zh-CN': '十二维得分总览（红 = 低于合格线 {passLine}）',
    'en-US': '12-Dimensional Score Overview (Red = Below Pass Line {passLine})',
  },
  qc_vis_overview_aria: {
    'zh-CN': '十二维得分总览条形图',
    'en-US': '12-Dimensional Score Overview Bar Chart',
  },
  qc_vis_pass_line: {
    'zh-CN': '合格线 {passLine}',
    'en-US': 'Pass Line {passLine}',
  },
  qc_vis_heatmap_title: {
    'zh-CN': '章节 × 维度 得分率热力图',
    'en-US': 'Chapter × Dimension Score Rate Heatmap',
  },
  qc_vis_heatmap_desc: {
    'zh-CN': '仅含提供章节粒度的 {count} 个维度；得分为维度内归一（相对该维度各章最高分）。',
    'en-US': 'Contains {count} dimensions with chapter granularity; scores normalized to chapter maximums.',
  },
  qc_vis_heatmap_aria: {
    'zh-CN': '章节维度得分率热力图',
    'en-US': 'Chapter-Dimension Score Rate Heatmap',
  },
  qc_vis_score_high: {
    'zh-CN': '得分率高',
    'en-US': 'High',
  },
  qc_vis_score_low: {
    'zh-CN': '低',
    'en-US': 'Low',
  },
  qc_vis_ch_label: {
    'zh-CN': '第{ch}章',
    'en-US': 'Ch.{ch}',
  },
  qc_vis_ch_tooltip: {
    'zh-CN': '{label}<br/>第 {ch} 章：得分率 {pct}%（原始 {raw}）',
    'en-US': '{label}<br/>Chapter {ch}: Score Rate {pct}% (Raw {raw})',
  },
  qc_vis_issue_title: {
    'zh-CN': '章节问题分布（按严重度）',
    'en-US': 'Chapter Issue Distribution (by Severity)',
  },
  qc_vis_issue_aria: {
    'zh-CN': '章节问题分布柱状图',
    'en-US': 'Chapter Issue Distribution Bar Chart',
  },
  qc_vis_sev_critical: {
    'zh-CN': '严重',
    'en-US': 'Critical',
  },
  qc_vis_sev_high: {
    'zh-CN': '高',
    'en-US': 'High',
  },
  qc_vis_sev_medium: {
    'zh-CN': '中',
    'en-US': 'Medium',
  },
  qc_vis_sev_low: {
    'zh-CN': '低',
    'en-US': 'Low',
  },

  // ==========================================
  // 专业叙事与分析图表 (Specialized Charts)
  // ==========================================
  chart_wave_series_current: {
    'zh-CN': '当前章节',
    'en-US': 'Current Chapter',
  },
  chart_wave_series_tension: {
    'zh-CN': '情绪张力',
    'en-US': 'Emotional Tension',
  },
  chart_wave_benchmark_default: {
    'zh-CN': '神作标杆基准',
    'en-US': 'Masterpiece Benchmark',
  },
  chart_wave_lbl_opening: {
    'zh-CN': '开端',
    'en-US': 'Opening',
  },
  chart_wave_lbl_foreshadow: {
    'zh-CN': '伏笔',
    'en-US': 'Foreshadowing',
  },
  chart_wave_lbl_microconflict: {
    'zh-CN': '微冲突',
    'en-US': 'Micro-conflict',
  },
  chart_wave_lbl_testing: {
    'zh-CN': '试探',
    'en-US': 'Testing',
  },
  chart_wave_lbl_accumulation: {
    'zh-CN': '积蓄',
    'en-US': 'Buildup',
  },
  chart_wave_lbl_outburst: {
    'zh-CN': '爆发',
    'en-US': 'Outburst',
  },
  chart_wave_lbl_climax: {
    'zh-CN': '高潮',
    'en-US': 'Climax',
  },
  chart_wave_lbl_breather: {
    'zh-CN': '喘息',
    'en-US': 'Breather',
  },
  chart_wave_lbl_counterattack: {
    'zh-CN': '反扑',
    'en-US': 'Counterattack',
  },
  chart_wave_lbl_resolution: {
    'zh-CN': '决胜',
    'en-US': 'Resolution',
  },
  chart_wave_lbl_linger: {
    'zh-CN': '留白',
    'en-US': 'Afterglow',
  },
  chart_rhythm_pacing: {
    'zh-CN': '爽点节奏',
    'en-US': 'Pacing & Reward',
  },
  chart_rhythm_faceslap: {
    'zh-CN': '打脸期待',
    'en-US': 'Anticipation',
  },
  chart_rhythm_infodensity: {
    'zh-CN': '信息密度',
    'en-US': 'Information Density',
  },
  chart_rhythm_goldenfinger: {
    'zh-CN': '金手指展开',
    'en-US': 'Core System',
  },
  chart_rhythm_hook: {
    'zh-CN': '章末钩子',
    'en-US': 'Chapter Cliffhanger',
  },
  chart_rhythm_conflict: {
    'zh-CN': '冲突升级',
    'en-US': 'Conflict Escalation',
  },
  chart_rhythm_series: {
    'zh-CN': '节奏综合评估',
    'en-US': 'Rhythm Evaluation',
  },
  chart_rate_daily_words: {
    'zh-CN': '每日字数',
    'en-US': 'Daily Words',
  },
  chart_rate_velocity: {
    'zh-CN': '平滑速率',
    'en-US': 'Smoothed Velocity',
  },
  chart_rate_y_words: {
    'zh-CN': '字数',
    'en-US': 'Words',
  },
  chart_rate_y_velocity: {
    'zh-CN': '速率 (字/天)',
    'en-US': 'Velocity (words/day)',
  },
  chart_wave_aria: {
    'zh-CN': '情绪起伏波形图',
    'en-US': 'Emotional Tension Wave Chart',
  },
  chart_wave_mark_climax_line: {
    'zh-CN': '高潮警戒线',
    'en-US': 'Climax Warning Line',
  },
  chart_wave_mark_climax_thresh: {
    'zh-CN': '高潮阈值 80',
    'en-US': 'Climax Threshold 80',
  },
  chart_rhythm_aria: {
    'zh-CN': '爽点节奏雷达图',
    'en-US': 'Pacing & Climax Radar Chart',
  },
  chart_rhythm_item_name: {
    'zh-CN': '网文爽感指数',
    'en-US': 'Catharsis Index',
  },
  chart_rate_aria: {
    'zh-CN': '创作速率与字数统计折线图',
    'en-US': 'Creation Rate & Word Count Line Chart',
  },
  chart_retention_aria: {
    'zh-CN': '商业网文读者留存流失预测图',
    'en-US': 'Commercial Reader Retention & Churn Chart',
  },
  chart_retention_rate: {
    'zh-CN': '读者留存率',
    'en-US': 'Reader Retention Rate',
  },
  chart_retention_start: {
    'zh-CN': '开局',
    'en-US': 'Opening',
  },
  chart_retention_point: {
    'zh-CN': '切片',
    'en-US': 'Segment',
  },
  chart_wave_empty: {
    'zh-CN': '暂无数据，请先测算',
    'en-US': 'No data yet. Run analysis to generate waveform.',
  },
  chart_retention_empty: {
    'zh-CN': '暂无数据，请先测算',
    'en-US': 'No data yet. Run retention analysis.',
  },
  chart_retention_tooltip_drop: {
    'zh-CN': '预估跳出',
    'en-US': 'Est. Drop-off',
  },
  chart_retention_tooltip_reason: {
    'zh-CN': '原因:',
    'en-US': 'Reason:',
  },
  chart_retention_churn: {
    'zh-CN': '累计流失',
    'en-US': 'Cumulative Churn',
  },
  chart_retention_line_s: {
    'zh-CN': 'S级线',
    'en-US': 'S-Tier',
  },
  chart_retention_line_a: {
    'zh-CN': 'A级线',
    'en-US': 'A-Tier',
  },
  chart_retention_line_pass: {
    'zh-CN': '及格线',
    'en-US': 'Pass Line',
  },
  chart_aria_bar: {
    'zh-CN': '柱状图',
    'en-US': 'Bar Chart',
  },
  chart_aria_pie: {
    'zh-CN': '饼图',
    'en-US': 'Pie Chart',
  },
  chart_aria_radar: {
    'zh-CN': '雷达图',
    'en-US': 'Radar Chart',
  },
  chart_aria_gauge: {
    'zh-CN': '仪表盘',
    'en-US': 'Gauge Chart',
  },
  chart_rhythm_empty: {
    'zh-CN': '暂无数据，请先测算',
    'en-US': 'No data yet. Run rhythm analysis.',
  },
  chart_rate_empty: {
    'zh-CN': '暂无数据，请先创作',
    'en-US': 'No writing data yet.',
  },

  // WritingExtras — 错误前缀 / 确认 / 模板 (i18n 补齐)
  extras_err_load_projects: {
    'zh-CN': '加载项目失败: {msg}',
    'en-US': 'Failed to load projects: {msg}',
  },
  extras_err_load_templates: {
    'zh-CN': '加载开篇模板失败: {msg}',
    'en-US': 'Failed to load opening templates: {msg}',
  },
  extras_err_apply_template: {
    'zh-CN': '应用黄金三章模板失败: {msg}',
    'en-US': 'Failed to apply Golden Three template: {msg}',
  },
  extras_err_apply_template_rollback: {
    'zh-CN': '应用黄金三章模板失败，已回滚 {count} 条已创建的大纲: {msg}',
    'en-US': 'Failed to apply Golden Three template, rolled back {count} outlines: {msg}',
  },
  extras_err_load_outlines: {
    'zh-CN': '加载大纲失败: {msg}',
    'en-US': 'Failed to load outlines: {msg}',
  },
  extras_err_title_required: {
    'zh-CN': '标题不能为空',
    'en-US': 'Title is required',
  },
  extras_err_save_failed: {
    'zh-CN': '保存失败: {msg}',
    'en-US': 'Failed to save: {msg}',
  },
  extras_err_delete_failed: {
    'zh-CN': '删除失败: {msg}',
    'en-US': 'Failed to delete: {msg}',
  },
  extras_err_update_status_failed: {
    'zh-CN': '更新状态失败: {msg}',
    'en-US': 'Failed to update status: {msg}',
  },
  extras_err_reorder_failed: {
    'zh-CN': '重排序失败: {msg}',
    'en-US': 'Failed to reorder: {msg}',
  },
  extras_err_load_characters: {
    'zh-CN': '加载人物卡失败: {msg}',
    'en-US': 'Failed to load characters: {msg}',
  },
  extras_err_random_name_failed: {
    'zh-CN': '随机起名失败: {msg}',
    'en-US': 'Failed to generate random name: {msg}',
  },
  extras_err_name_required: {
    'zh-CN': '姓名不能为空',
    'en-US': 'Name is required',
  },
  extras_err_load_notes: {
    'zh-CN': '加载便签失败: {msg}',
    'en-US': 'Failed to load notes: {msg}',
  },
  extras_err_title_content_empty: {
    'zh-CN': '标题与内容不能同时为空',
    'en-US': 'Title and content cannot both be empty',
  },
  extras_err_load_dashboard: {
    'zh-CN': '加载仪表盘统计失败: {msg}',
    'en-US': 'Failed to load dashboard stats: {msg}',
  },
  extras_err_tension_failed: {
    'zh-CN': '张力分析失败: {msg}',
    'en-US': 'Tension analysis failed: {msg}',
  },
  extras_err_golden_three_failed: {
    'zh-CN': '黄金三章比对失败: {msg}',
    'en-US': 'Golden Three comparison failed: {msg}',
  },
  extras_err_retention_failed: {
    'zh-CN': '读者留存测算失败: {msg}',
    'en-US': 'Reader retention estimation failed: {msg}',
  },
  extras_confirm_delete_outline: {
    'zh-CN': '确定删除这条大纲吗？',
    'en-US': 'Delete this outline item?',
  },
  extras_confirm_delete_character: {
    'zh-CN': '确定删除这张人物卡吗？',
    'en-US': 'Delete this character card?',
  },
  extras_confirm_delete_note: {
    'zh-CN': '确定删除这条便签吗？',
    'en-US': 'Delete this note?',
  },
  extras_template_ch1_title: {
    'zh-CN': '第1章：{name}（首章生死危机）',
    'en-US': 'Ch 1: {name} (Opening Crisis)',
  },
  extras_template_ch2_title: {
    'zh-CN': '第2章：{name}（压迫激化与转机）',
    'en-US': 'Ch 2: {name} (Escalation & Turning Point)',
  },
  extras_template_ch3_title: {
    'zh-CN': '第3章：{name}（首爽破局与爽点兑现）',
    'en-US': 'Ch 3: {name} (First Payoff & Breakthrough)',
  },
  extras_template_ch1_summary: {
    'zh-CN': '【前300字钩子】\n{first300Words}\n\n【第一章节拍】\n{beat}',
    'en-US': '[Hook — First 300 Words]\n{first300Words}\n\n[Chapter 1 Beat]\n{beat}',
  },
  extras_template_ch2_summary: {
    'zh-CN': '【第二章节拍】\n{beat}',
    'en-US': '[Chapter 2 Beat]\n{beat}',
  },
  extras_template_ch3_summary: {
    'zh-CN': '【第三章节拍】\n{beat}',
    'en-US': '[Chapter 3 Beat]\n{beat}',
  },
  extras_outline_reorder_hint: {
    'zh-CN': '支持上下微移原子重排',
    'en-US': 'Supports fine-grained reorder via up/down moves',
  },
  extras_char_subtitle: {
    'zh-CN': '支持人物阵营与人物关系网络关联',
    'en-US': 'Supports faction alignment and character relationship network',
  },
  extras_char_subtitle_count: {
    'zh-CN': '当前共 {count} 位角色 ｜ {hint}',
    'en-US': '{count} characters ｜ {hint}',
  },
  extras_action_toggle_status: {
    'zh-CN': '点击切换状态',
    'en-US': 'Click to toggle status',
  },
  extras_action_move_up: {
    'zh-CN': '上移',
    'en-US': 'Move up',
  },
  extras_action_move_down: {
    'zh-CN': '下移',
    'en-US': 'Move down',
  },
  extras_action_edit: {
    'zh-CN': '编辑',
    'en-US': 'Edit',
  },
  extras_action_delete: {
    'zh-CN': '删除',
    'en-US': 'Delete',
  },
  extras_char_relation_prefix: {
    'zh-CN': '关系：与 ',
    'en-US': 'Relation: with ',
  },
  extras_char_relation_middle: {
    'zh-CN': ' 为 ',
    'en-US': ' as ',
  },
  extras_char_relation_default: {
    'zh-CN': '关联',
    'en-US': 'Related',
  },
  extras_retention_grade_label: {
    'zh-CN': '综合评级 {grade} · {desc}',
    'en-US': 'Grade {grade} · {desc}',
  },
  extras_retention_hotspot_item: {
    'zh-CN': '[{level}] {label}（预估跳出 {pct}%）：{reason} → {fix}',
    'en-US': '[{level}] {label} (est. drop {pct}%): {reason} → {fix}',
  },

  // ==========================================
  // WritingWorkbench InlineGuide (WS-A5)
  // ==========================================
  guide_inject_what: {
    'zh-CN': '把拆书得到的资产卡拼成一段完整的写作 Prompt：决定「用谁的声音、按什么规则」写，后面生成章节都会按这套风格来。',
    'en-US': 'Assemble analyzed asset cards into a unified writing prompt — pick the voice, rules, and style your chapters will follow.',
  },
  guide_inject_step_1: {
    'zh-CN': 'voice-card 必选：决定人物声线和叙事风格（来自你拆过的书）。',
    'en-US': 'voice-card is required: sets narrative voice and tone (from a deconstructed book).',
  },
  guide_inject_step_2: {
    'zh-CN': '可选叠加：genre-pack（题材规则）、craft-card（笔法技巧）、蒸馏规则（多本书提炼出的通用规律）、prose-card（跨题材文风参照）。',
    'en-US': 'Optional layers: genre-pack, craft-card, distilled rules (cross-book synthesis), prose-card (cross-genre voice reference).',
  },
  guide_inject_step_3: {
    'zh-CN': '点「生成 Prompt」可以预览拼好的提示词，确认风格对不对。',
    'en-US': 'Click "Generate Prompt" to preview the assembled prompt and verify the style.',
  },
  guide_inject_step_4: {
    'zh-CN': '这里选好的 voice-card 与 genre-pack，「写作」页签生成章节时会自动用上（同一份选择）。',
    'en-US': 'The voice-card & genre-pack selected here carry over automatically when generating chapters.',
  },
  guide_inject_tip_1: {
    'zh-CN': '资产列表是空的？先去「分析」工作台导入一本书并完成拆书。',
    'en-US': 'Asset list empty? Import a book in the Analysis workbench first.',
  },
  guide_inject_tip_2: {
    'zh-CN': '蒸馏规则是离线统计生成的，不需要配置 AI 模型也能用。',
    'en-US': 'Distilled rules are generated offline — no AI model needed.',
  },
  guide_inject_tip_3: {
    'zh-CN': 'voice 与其他资产题材不一致时，后端会按铁律一拒绝（400），请换成同题材资产。',
    'en-US': 'If voice genre mismatches other assets, the backend rejects (400) per Genre Isolation. Use same-genre assets.',
  },
  guide_generate_what: {
    'zh-CN': '按你的「写作要点」生成新章节：模型写出初稿后自动打分，不达标就自动改写，直到达标或用完改写次数。写好的章节会落盘保存。',
    'en-US': 'Generate a chapter from your brief: the model drafts, auto-scores, and rewrites until it passes. Finished chapters are saved to disk.',
  },
  guide_generate_step_1: {
    'zh-CN': '选项目：项目就是用户数据目录 novel/ 下的文件夹——在 novel/ 下新建一个文件夹，就是一个新写作项目。',
    'en-US': 'Pick a project: each project is a folder under the novel/ data directory.',
  },
  guide_generate_step_2: {
    'zh-CN': 'voice-card 与 genre-pack 沿用「注入」页签的选择（同一份），这里可以直接调整。',
    'en-US': 'voice-card & genre-pack carry over from the Asset Injection tab; adjust here if needed.',
  },
  guide_generate_step_3: {
    'zh-CN': '选章节号、写「写作要点」：交代本章发生什么、谁出场、情绪走向、字数和结尾要求，越具体越好。',
    'en-US': 'Set chapter number and write the brief: what happens, who appears, emotional arc, word count & ending — be specific.',
  },
  guide_generate_step_4: {
    'zh-CN': '点「开始写作」，进度实时显示；完成后会提示章节文件的保存位置。',
    'en-US': 'Click "Start Writing" — progress streams live; the save path is shown on completion.',
  },
  guide_generate_example: {
    'zh-CN': '第5章：深秋傍晚，温霜禾抱着一摞粉色包装的礼物盒走进澜州老街的奶茶店，点了七分糖的芋泥波波奶茶。江春屿跟在后面替她拎包。两人因为"谁请客"斗嘴，温霜禾说了句"随便吧"——其实是生气了。要求：2200字左右，对话占四成，结尾留钩子：温霜禾发现奶茶店落地窗外站着一个熟悉的身影。',
    'en-US': 'Ch.5: Late-autumn dusk. Wen Shuanghe enters a milk-tea shop on old-town Lanzhou with pink gift boxes, ordering 70%-sugar taro bubble tea. Jiang Chunyu follows, carrying her bags. They banter over who pays; "whatever" from Wen Shuanghe signals she is actually upset. ~2200 chars, 40% dialogue; cliffhanger: a familiar figure outside the window.',
  },
  guide_generate_tip_1: {
    'zh-CN': '没配 AI 模型也能用：会进入降级模式，生成一份「AI接管写作任务.md」指引，你可以手动写完，再用下面的「手动入库」贴回来打分。',
    'en-US': 'Works without an AI model too: generates an "AI Takeover Task" guide you can write manually and score via Manual Import.',
  },
  guide_generate_tip_2: {
    'zh-CN': '「写作要点」决定了章节质量：只写"写一章校园恋爱"效果会很差，把人物、场景、冲突、字数都写清楚。',
    'en-US': 'Brief quality matters: "write a romance chapter" produces weak results — spell out characters, scenes, conflicts, and length.',
  },
  guide_score_what: {
    'zh-CN': '给一段章节正文打分：从「风格一致性」（像不像这张声线卡的味道）和「写作质量」（有没有硬伤）两个维度判定，低于及格线会列出具体问题。',
    'en-US': 'Score a chapter draft on two axes: voice consistency (does it match the voice-card?) and craft quality (any hard flaws?). Below-threshold scores come with specifics.',
  },
  guide_score_step_1: {
    'zh-CN': '选一张 voice-card 作为参照标准。',
    'en-US': 'Select a voice-card as the reference standard.',
  },
  guide_score_step_2: {
    'zh-CN': '把章节正文粘贴进来，点「打分」。',
    'en-US': 'Paste your chapter text and click "Score".',
  },
  guide_score_step_3: {
    'zh-CN': '看综合判定：一致性得分 + 质量得分，以及五维明细和质量问题列表。',
    'en-US': 'Review the verdict: consistency score + quality score with breakdown and issue list.',
  },
  guide_score_step_4: {
    'zh-CN': '分数不够就按列出的问题改，改完可以再打一次。',
    'en-US': 'If the score is low, revise per the listed issues and score again.',
  },
  guide_score_tip_1: {
    'zh-CN': '及格线可以在「设置」工作台里调整。',
    'en-US': 'Pass threshold is adjustable in the Settings workbench.',
  },
  guide_score_tip_2: {
    'zh-CN': '打分不需要 AI 模型，是本地规则引擎跑的。',
    'en-US': 'Scoring runs on a local rule engine — no AI model needed.',
  },
  guide_assemble_what: {
    'zh-CN': '把一本书多轮拆书（pass1-5）的产出组装成正式资产并入库：书名选已完成全部 pass 的书，填上题材，组装后资产就能在注入和写作里用了。',
    'en-US': 'Assemble pass1-5 outputs of a deconstructed book into formal, indexed assets: pick a completed book, set its genre, and register the cards.',
  },
  guide_assemble_step_1: {
    'zh-CN': '从下拉里选一本已完成 pass1-5 的书。',
    'en-US': 'Pick a book that has completed all pass1-5 analysis.',
  },
  guide_assemble_step_2: {
    'zh-CN': '填写题材（如：校园、玄幻、悬疑）——题材决定了资产的隔离分组，填错会导致注入时选不到。',
    'en-US': 'Enter genre (e.g., campus, fantasy, mystery) — genre is the isolation boundary for assets.',
  },
  guide_assemble_step_3: {
    'zh-CN': '点「组装入库」，产出 voice-card / structure-obs 等正式资产。',
    'en-US': 'Click "Assemble & Index" to produce voice-card, structure-obs, and other formal assets.',
  },
  guide_assemble_tip_1: {
    'zh-CN': '列表是空的？说明还没有书跑完 pass1-5，先去「分析」工作台完成拆书。',
    'en-US': 'Empty? No book has finished pass1-5 yet — run Analysis first.',
  },
}

// ---------------------------------------------------------------------------
// Context-free translation accessor（2026-11-02）
//
// 非 React 组件里的纯函数需要按当前语言取文案（典型：api/client.ts 的
// friendlyError）。这些地方拿不到 useI18n()，过去只能硬编码中文，导致英文
// 界面下错误提示仍是中文。I18nProvider 在 locale 变化时调 setActiveLocale 同步。
// ---------------------------------------------------------------------------
let activeLocale: Locale = 'zh-CN'

export function setActiveLocale(locale: Locale): void {
  activeLocale = locale
}

export function getActiveLocale(): Locale {
  return activeLocale
}

/** 按当前激活语言取词条；缺条目回落到 fallback，再回落到 key 本身。 */
export function tGlobal(key: string, fallback?: string): string {
  const entry = TRANSLATIONS[key]
  const raw = entry && entry[activeLocale] !== undefined ? entry[activeLocale] : (fallback ?? key)
  return raw
}
