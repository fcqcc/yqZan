const api = require('../../utils/api')
Page({
  data: { level: 1, current_exp: 0, next_level_exp: 1, progress_pct: 0, logs: [] },
  onShow() { this.load() },
  async load() {
    try {
      const [lvl, logs] = await Promise.all([api.getLevel(), api.getLevelLogs()])
      this.setData({ level: lvl.level, current_exp: lvl.current_exp, next_level_exp: lvl.next_level_exp, progress_pct: lvl.progress_pct, logs: logs || [] })
    } catch(e) {}
  }
})