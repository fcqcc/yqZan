// pages/home/home.js
const api = require('../../utils/api')

function fmtMoney(n) {
  if (n >= 100000000) return '¥' + (n/100000000).toFixed(1) + '亿'
  if (n >= 10000) return '¥' + (n/10000).toFixed(1) + '万'
  return '¥' + n.toLocaleString()
}

// ---------- 宠物辅助 ----------
const PET_EMOJI_MAP = [
  { max: 20, emoji: '🥚', anim: 'pet-sleep', name: '小蛋蛋', desc: '刚刚孵化的小家伙，需要你的关爱才能长大……' },
  { max: 40, emoji: '🐣', anim: 'pet-walk-slow', name: '小绒球', desc: '已经开始摇摇晃晃地走动了！' },
  { max: 60, emoji: '🐰', anim: 'pet-walk', name: '蹦蹦', desc: '活泼好动，每天都在成长～' },
  { max: 80, emoji: '🦊', anim: 'pet-excited', name: '小灵狐', desc: '充满灵性，和你越来越亲密了！' },
  { max: 100, emoji: '🦄', anim: 'pet-magic', name: '梦幻独角兽', desc: '你们的爱情已经升华到最美好的境界 ✨' }
]

function getPetConfig(intimacy) {
  const lv = Math.min(Math.max(intimacy || 0, 0), 100)
  for (const cfg of PET_EMOJI_MAP) {
    if (lv <= cfg.max) return cfg
  }
  return PET_EMOJI_MAP[PET_EMOJI_MAP.length - 1]
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
    plan_count: 0, anni_count: 0, gift_count: 0, together_days: 0,
    // 宠物 & 扭蛋
    pet: null,
    petEmoji: '🥚',
    petAnimationClass: 'pet-sleep',
    petName: '小蛋蛋',
    intimacyLevel: 0,
    intimacyPct: 0,
    petDescription: '刚刚孵化的小家伙，需要你的关爱才能长大……',
    petId: null,
    tickets: 0,
    showPetModal: false,
    feeding: false,
    sparkCount: 0,
    sparkStatus: 'active',
    maxSpark: 0,
    streakDays: 0
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) { wx.reLaunch({ url: '/pages/login/login' }); return }
    this.setData({ userInfo })
    this.loadData()
    this.loadPetData()
    // 自动签到
    api.doCheckin().catch(() => {})
    this.loadSpark()
  },

  async loadSpark() {
    try {
      const s = await api.getSpark()
      this.setData({
        sparkCount: s.spark_count || 0,
        sparkStatus: s.spark_status || 'active',
        maxSpark: s.max_spark_count || 0,
        streakDays: s.streak_days || 0,
      })
    } catch(e) {}
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

  go(e) { 
    const url = e.currentTarget.dataset.url
    if (url === '/pages/plans/plans') {
      wx.switchTab({ url })
    } else {
      wx.navigateTo({ url })
    }
  },
  goTab(e) { wx.switchTab({ url: e.currentTarget.dataset.url }) },
  goBind() { wx.switchTab({ url: '/pages/settings/settings' }) },

  // ===== 宠物 & 扭蛋 =====

  async loadPetData() {
    try {
      const [petRes, ticketsRes] = await Promise.all([
        api.getActivePet().catch(() => null),
        api.getTickets().catch(() => ({ tickets: 0 }))
      ])
      this.updatePetUI(petRes)
      this.setData({ tickets: ticketsRes.tickets || 0 })
    } catch (e) { console.error('loadPetData', e) }
  },

  updatePetUI(pet) {
    if (!pet) {
      this.setData({
        pet: null, petId: null,
        petEmoji: '🥚', petAnimationClass: 'pet-sleep',
        petName: '小蛋蛋', intimacyLevel: 0, intimacyPct: 0,
        petDescription: '还没有领养宠物哦～'
      })
      return
    }
    const intimacy = pet.intimacy ?? 0
    const cfg = getPetConfig(intimacy)
    this.setData({
      pet,
      petId: pet.id,
      petEmoji: cfg.emoji,
      petAnimationClass: cfg.anim,
      petName: pet.name || cfg.name,
      intimacyLevel: intimacy,
      intimacyPct: Math.min(100, Math.round(intimacy)),
      petDescription: cfg.desc
    })
  },

  showPetModal() {
    this.setData({ showPetModal: true })
  },

  hidePetModal() {
    this.setData({ showPetModal: false })
  },

  stopPropagation() {},

  async feedCurrentPet() {
    if (this.data.feeding) return
    const { petId } = this.data
    if (!petId) {
      wx.showToast({ title: '还没有宠物', icon: 'none' })
      return
    }
    this.setData({ feeding: true })
    try {
      wx.showLoading({ title: '投喂中…' })
      const res = await api.feedPet(petId)
      wx.hideLoading()
      wx.showToast({ title: '投喂成功 ❤️', icon: 'none' })
      // 刷新宠物状态
      this.loadPetData()
      this.loadData()
    } catch (e) {
      wx.hideLoading()
      if (e.errMsg && e.errMsg.includes('429')) {
        wx.showToast({ title: '宠物刚吃过，等一会儿再喂吧', icon: 'none' })
      } else {
        wx.showToast({ title: e.errMsg || '投喂失败', icon: 'none' })
      }
    } finally {
      this.setData({ feeding: false })
    }
  }
})
