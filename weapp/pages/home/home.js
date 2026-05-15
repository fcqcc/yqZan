// pages/home/home.js
const api = require('../../utils/api')

function fmtMoney(n) {
  if (n >= 100000000) return '¥' + (n/100000000).toFixed(1) + '亿'
  if (n >= 10000) return '¥' + (n/10000).toFixed(1) + '万'
  return '¥' + n.toLocaleString()
}

Page({
  data: {
    userInfo: null, partner: null,
    level: 1, current_exp: 0, next_level_exp: 1, progress_pct: 0,
    delivered_text: '¥0', target_text: '¥0',
    current_amount: 0, target_amount: 0, plan_progress: 0,
    nearestAnni: null,
    pendingTodos: [],
    latestNote: null,
    plan_count: 0, anni_count: 0, gift_count: 0, together_days: 0
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) { wx.reLaunch({ url: '/pages/login/login' }); return }
    this.setData({ userInfo })
    this.loadData()
  },

  async loadData() {
    try {
      const [plans, anniversaries, level, snapshot, partner, todos, notes] = await Promise.all([
        api.getPlans().catch(() => []),
        api.getAnniversaries().catch(() => []),
        api.getLevel().catch(() => ({ level: 1, progress_pct: 0, current_exp: 0, next_level_exp: 1 })),
        api.getCardSnapshot().catch(() => ({})),
        api.getPartner().catch(() => null),
        api.getTodos().catch(() => []),
        api.getNotes().catch(() => ({ notes: [] }))
      ])

      // 存钱进度 - 取第一个未完成的计划
      const activePlan = plans.find(p => !p.done) || plans[0]
      const cur = activePlan ? activePlan.current_amount || 0 : 0
      const tar = activePlan ? activePlan.target_amount || 1 : 1

      // 今日待办 - 未完成的事项
      const pendingTodos = todos.filter(t => !t.done).slice(0, 3)

      // 最新便利贴
      const noteList = notes.notes || []
      const latestNote = noteList.length > 0 ? noteList[0] : null

      this.setData({
        partner,
        level: level.level || 1,
        current_exp: level.current_exp || 0,
        next_level_exp: level.next_level_exp || 1,
        progress_pct: level.progress_pct || 0,
        delivered_text: fmtMoney(snapshot.total_delivered || cur),
        target_text: fmtMoney(snapshot.total_target || tar),
        current_amount: cur,
        target_amount: tar,
        plan_progress: Math.min(cur / Math.max(tar, 1) * 100, 100),
        ringDeg: Math.min(cur / Math.max(tar, 1) * 360, 360),
        plan_pct_text: Math.min(Math.round(cur / Math.max(tar, 1) * 100), 100) + '%',
        nearestAnni: this.findNearestAnni(anniversaries),
        pendingTodos,
        latestNote,
        plan_count: plans.length,
        anni_count: anniversaries.length,
        gift_count: snapshot.gift_count || 0,
        together_days: snapshot.together_days || 0
      })
    } catch(e) { console.error(e) }
  },

  findNearestAnni(anniversaries) {
    const now = new Date()
    let nearest = null
    for (const a of anniversaries) {
      const p = a.date_val.split('-')
      if (p.length < 3) continue
      const d = new Date(now.getFullYear(), parseInt(p[1]) - 1, parseInt(p[2]))
      if (d < now) d.setFullYear(d.getFullYear() + 1)
      const days = Math.ceil((d - now) / 86400000)
      if (!nearest || days < nearest.days) nearest = { title: a.title, days, date: a.date_val }
    }
    return nearest
  },

  go(e) { wx.navigateTo({ url: e.currentTarget.dataset.url }) },
  goTab(e) { wx.switchTab({ url: e.currentTarget.dataset.url }) },
  goBind() { wx.switchTab({ url: '/pages/settings/settings' }) }
})
