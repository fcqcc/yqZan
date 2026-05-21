// pages/level/level.js
const api = require('../../utils/api')
Page({
  data: { level: 1, current_exp: 0, next_level_exp: 1, progress_pct: 0, logs: [], unlocks: [], nextUnlock: null },
  onShow() { this.load() },
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
      this.setData({
        level: lvl.level,
        current_exp: lvl.current_exp,
        next_level_exp: lvl.next_level_exp,
        progress_pct: lvl.progress_pct,
        logs,
        unlocks: unlocksRes ? unlocksRes.unlocked || [] : [],
        nextUnlock: unlocksRes ? unlocksRes.next_unlock : null,
      })
    } catch (e) {}
  }
})
