// pages/level/level.js
const api = require('../../utils/api')
Page({
  data: { level: 1, current_exp: 0, next_level_exp: 1, progress_pct: 0, logs: [], unlocks: [], nextUnlock: null, levelTitle: '甜蜜恋人', expRemaining: 0, uiTheme: getApp().globalData.uiTheme || 'handdrawn' },
  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    this.load()
  },
  async load() {
    try {
      const [lvl, logsRes, unlocksRes] = await Promise.all([
        api.getLevel(),
        api.getLevelLogs(),
        api.getLevelUnlocks().catch(() => null),
      ])
      const logsRaw = Array.isArray(logsRes) ? logsRes : (logsRes && logsRes.logs) || []
      const logs = (logsRaw || []).map((item) => ({
        ...item,
        logDate:
          item.created_at != null
            ? String(item.created_at).slice(0, 16)
            : ''
      }))
      const levelTitles = ['新手情侣', '甜蜜恋人', '默契搭档', '攒钱达人', '幸福满级']
      const titleIdx = Math.min(Math.floor((lvl.level || 1) / 10), levelTitles.length - 1)
      const expRemaining = Math.max(0, (lvl.next_level_exp || 0) - (lvl.current_exp || 0))
      this.setData({
        level: lvl.level,
        current_exp: lvl.current_exp,
        next_level_exp: lvl.next_level_exp,
        progress_pct: lvl.progress_pct,
        levelTitle: levelTitles[titleIdx] || '甜蜜恋人',
        expRemaining,
        logs,
        unlocks: unlocksRes ? unlocksRes.unlocked || [] : [],
        nextUnlock: unlocksRes ? unlocksRes.next_unlock : null,
      })
    } catch (e) {}
  }
})
