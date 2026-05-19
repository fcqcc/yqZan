// pages/home/home.js
const api = require('../../utils/api')

function fmtMoney(n) {
  if (n >= 100000000) return '¥' + (n/100000000).toFixed(1) + '亿'
  if (n >= 10000) return '¥' + (n/10000).toFixed(1) + '万'
  return '¥' + n.toLocaleString()
}

function wrapPlan(p) {
  const cur = Number(p.current_amount) || 0
  const tar = Math.max(Number(p.target_amount) || 1, 1)
  return {
    ...p,
    progressPct: Math.min(100, (cur / tar) * 100),
    _curText: fmtMoney(cur),
    _tarText: fmtMoney(tar)
  }
}

Page({
  data: {
    tabBarIndex: 0,
    userInfo: null, partner: null,
    level: 1, current_exp: 0, next_level_exp: 1, progress_pct: 0,
    delivered_text: '¥0', target_text: '¥0',
    current_amount: 0, target_amount: 0, plan_progress: 0,
    nearestAnni: null,
    plans: [],
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
      const [plans, anniversaries, level, snapshot, partner] = await Promise.all([
        api.getPlans().catch(() => []),
        api.getAnniversaries().catch(() => []),
        api.getLevel().catch(() => ({ level: 1, progress_pct: 0, current_exp: 0, next_level_exp: 1 })),
        api.getCardSnapshot().catch(() => ({})),
        api.getPartner().catch(() => null)
      ])

      // 存钱进度 - 所有计划汇总
      const validPlans = Array.isArray(plans) ? plans : []
      const planList = validPlans.map(wrapPlan)
      const totalCur = planList.reduce((s, p) => s + (Number(p.current_amount) || 0), 0)
      const totalTar = planList.reduce((s, p) => s + (Number(p.target_amount) || 0), 0)
      const activePlan = planList.find(p => !p.done) || planList[0]
      const cur = activePlan ? activePlan.current_amount || 0 : 0
      const tar = activePlan ? activePlan.target_amount || 1 : 1

      this.setData({
        partner,
        plans: planList,
        level: level.level || 1,
        current_exp: level.current_exp || 0,
        next_level_exp: level.next_level_exp || 1,
        progress_pct: level.progress_pct || 0,
        delivered_text: fmtMoney(snapshot.total_delivered || totalCur),
        target_text: fmtMoney(snapshot.total_target || totalTar),
        current_amount: totalCur,
        target_amount: totalTar,
        plan_progress: Math.min(totalCur / Math.max(totalTar, 1) * 100, 100),
        nearestAnni: this.findNearestAnni(anniversaries),
        plan_count: planList.length,
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
