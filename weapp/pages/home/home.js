// pages/home/home.js
const api = require('../../utils/api')

Page({
  data: {
    userInfo: null,
    partner: null,
    level: 0,
    plans: [],
    wishes: [],
    anniversaries: [],
    nearestAnni: null,
    stats: { plan_count: 0, done_plans: 0, wish_count: 0, anni_count: 0 }
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) { wx.reLaunch({ url: '/pages/login/login' }); return }
    this.setData({ userInfo })
    this.loadData()
  },

  async loadData() {
    try {
      const [plans, wishes, anniversaries, level, snapshot, partner] = await Promise.all([
        api.getPlans().catch(() => []),
        api.getWishes().catch(() => []),
        api.getAnniversaries().catch(() => []),
        api.getLevel().catch(() => ({ level: 1, progress_pct: 0 })),
        api.getCardSnapshot().catch(() => ({})),
        api.getPartner().catch(() => null)
      ])

      this.setData({
        plans, wishes, anniversaries, partner,
        level: level.level || 1,
        progress_pct: level.progress_pct || 0,
        current_level_exp: level.current_exp || 0,
        next_level_exp: level.next_level_exp || 1,
        stats: {
          plan_count: plans.length || 0,
          total_delivered: snapshot.total_delivered || 0,
          done_todos: snapshot.done_todos || 0,
          wish_rate: snapshot.wish_rate || 0,
          anni_count: anniversaries.length || 0
        },
        nearestAnni: this.findNearestAnni(anniversaries)
      })
    } catch (e) { console.error(e) }
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
  goBind() { wx.navigateTo({ url: '/pages/settings/settings' }) }
})
