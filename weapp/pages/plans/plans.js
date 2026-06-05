// pages/plans/plans.js
let api = require('../../utils/api')
const theme = require('../../utils/theme')
let appConfig = require('../../utils/config')

function fmtNum(n) {
  if (n == null || isNaN(n)) return '0'
  try {
    return Number(n).toLocaleString()
  } catch(e) {
    return String(n)
  }
}

function pad2(n) {
  return (n < 10 ? '0' : '') + n
}

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate()
}

function buildYears(centerY) {
  const years = []
  const start = centerY - 2
  const end = centerY + 10
  for (let y = start; y <= end; y++) years.push(y)
  return years
}

function buildMonths() {
  const months = []
  for (let i = 1; i <= 12; i++) months.push(i)
  return months
}

function buildDays(y, m) {
  const max = daysInMonth(y, m)
  const days = []
  for (let i = 1; i <= max; i++) days.push(i)
  return days
}

const COLOR_CLASSES = ['pink', 'orange', 'blue', 'green']

function wrapPlan(p, idx) {
  const cur = Number(p.current_amount) || 0
  const tar = Math.max(Number(p.target_amount) || 1, 1)
  const hasEmbed = p != null && Object.prototype.hasOwnProperty.call(p, 'deliveries')
  const embedList = hasEmbed ? normalizeDeliveries(p.deliveries) : []
  const deliveries = embedList.map((d) => ({
    ...d,
    _when: formatWhen(d.created_at || d.delivered_at || d.at)
  }))
  const remain = Math.max(0, tar - cur)
  // 日期范围
  let dateRange = ''
  if (p.created_at) {
    dateRange = String(p.created_at).slice(0, 10).replace(/-/g, '.')
    if (p.deadline_date) dateRange += ' - ' + String(p.deadline_date).replace(/-/g, '.')
  } else if (p.deadline_date) {
    dateRange = String(p.deadline_date).replace(/-/g, '.')
  }
  return {
    ...p,
    expanded: false,
    deliveries,
    deliveriesLoaded: hasEmbed,
    deliveriesLoading: false,
    progressPct: Math.min(100, Math.round((cur / tar) * 100)),
    _curText: fmtNum(cur),
    _tarText: fmtNum(tar),
    _remainText: fmtNum(remain),
    _dateRange: dateRange,
    colorClass: COLOR_CLASSES[idx % COLOR_CLASSES.length],
    icon: p.icon || (p.done ? '✅' : ['🏝️', '🏠', '🎁', '💰'][idx % 4]),
  }
}

function normalizeDeliveries(res) {
  if (Array.isArray(res)) return res
  if (res && Array.isArray(res.deliveries)) return res.deliveries
  if (res && Array.isArray(res.items)) return res.items
  return []
}

function formatWhen(s) {
  if (!s) return ''
  const str = String(s)
  if (str.length >= 16) return str.slice(0, 16).replace('T', ' ')
  return str.slice(0, 10)
}

/** 礼花粒子（MC 图腾感） */
function buildTotemParticles(count = 44, idOffset = 0) {
  const colors = [
    '#ffeb3b', '#ffc107', '#ff9800', '#ff7043', '#fff59d', '#ffffff',
    '#f48fb1', '#ce93d8', '#80deea', '#b9f6ca'
  ]
  const dirs = 12
  const list = []
  for (let i = 0; i < count; i++) {
    list.push({
      id: idOffset + i,
      dir: (i + 3) % dirs,
      delay: (Math.random() * 0.18).toFixed(3),
      dur: (0.85 + Math.random() * 0.45).toFixed(2),
      size: Math.round(4 + Math.random() * 7),
      color: colors[i % colors.length],
      square: Math.random() > 0.35
    })
  }
  return list
}

Page({
  data: {
    plans: [],
    showForm: false,
    title: '',
    target: '',
    deadlineDate: '',
    showDeadlinePicker: false,
    deadlineYears: [],
    deadlineMonths: [],
    deadlineDays: [],
    deadlinePickerIdx: [0, 0, 0],
    showDeliver: false,
    planId: null,
    amount: '',
    note: '',
    deliverCompleteDate: '',
    deliverCompleteTime: '',
    showTotemCelebrate: false,
    totemPlan: null,
    totemParticles: [],
    totemCloseAction: 'none',
    totemPlanId: null,
    // 存钱动效
    showCoinEffect: false,
    coinParticles: [],
    lastAmount: '0',
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
  },

  onLoad() {
    this.setData(theme.getNavLayout())
    this.setData({ canGoBack: getCurrentPages().length > 1 })
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    // 直接判断 token，不依赖 behavior 的时序
    const token = wx.getStorageSync('token')
    if (!token) {
      this.setData({ isGuest: true })
      return
    }
    this.load()
  },

  onUnload() {
    if (this._totemBurstTimer) {
      clearTimeout(this._totemBurstTimer)
      this._totemBurstTimer = null
    }
    if (this._coinTimer) {
      clearTimeout(this._coinTimer)
      this._coinTimer = null
    }
  },

  async load() {
    try {
      const raw = await api.getPlans()
      const list = Array.isArray(raw) ? raw : []
      const plans = list.map((p, i) => wrapPlan(p, i))
      const totalSaved = plans.reduce((s, p) => s + (Number(p.current_amount) || 0), 0)
      const activeCount = plans.filter(p => !p.done).length
      const doneCount = plans.filter(p => p.done).length

      // 本月已存
      const now = new Date()
      const monthPrefix = `${now.getFullYear()}-${pad2(now.getMonth()+1)}`
      let monthSaved = 0
      for (const p of list) {
        const dels = p.deliveries || []
        for (const d of dels) {
          const dDate = String(d.created_at || d.date || '').slice(0, 7)
          if (dDate === monthPrefix) monthSaved += Number(d.amount || 0)
        }
      }

      // 近6月趋势
      const trendBars = []
      const months = ['','1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
      let maxMonth = 0
      const monthlyTotals = []
      for (let i = 5; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
        const prefix = `${d.getFullYear()}-${pad2(d.getMonth()+1)}`
        let total = 0
        for (const p of list) {
          const dels = p.deliveries || []
          for (const dd of dels) {
            const ddDate = String(dd.created_at || dd.date || '').slice(0, 7)
            if (ddDate === prefix) total += Number(dd.amount || 0)
          }
        }
        monthlyTotals.push(total)
        if (total > maxMonth) maxMonth = total
      }
      for (let i = 0; i < 6; i++) {
        const d = new Date(now.getFullYear(), now.getMonth() - 5 + i, 1)
        const pct = maxMonth > 0 ? (monthlyTotals[i] / maxMonth) * 100 : 0
        trendBars.push({
          label: months[d.getMonth() + 1],
          height: Math.max(8, pct) + '%',
          isMax: monthlyTotals[i] === maxMonth,
        })
      }

      this.setData({
        plans, totalSaved, activeCount, doneCount,
        monthSaved: fmtNum(monthSaved),
        trendBars,
      })
      this.checkCongratulate(plans)
    } catch (e) {
      this.setData({ plans: [], totalSaved: 0, activeCount: 0, doneCount: 0, monthSaved: '0', trendBars: [] })
    }
  },

  toggleForm() {
    if (this.data.isGuest) return this._guestPrompt()
    this.setData({
      showForm: !this.data.showForm,
      title: '',
      target: '',
      deadlineDate: '',
      showDeadlinePicker: false
    })
  },

  openDeadlinePicker() {
    const now = new Date()
    let y = now.getFullYear()
    let m = now.getMonth() + 1
    let d = now.getDate()
    const cur = this.data.deadlineDate
    if (cur && /^\d{4}-\d{2}-\d{2}$/.test(cur)) {
      const p = cur.split('-').map(Number)
      y = p[0]
      m = p[1]
      d = p[2]
    }
    const years = buildYears(y)
    const months = buildMonths()
    const yIdx = Math.max(0, years.indexOf(y))
    const mIdx = Math.min(11, Math.max(0, m - 1))
    const ySel = years[yIdx]
    const mSel = months[mIdx]
    const days = buildDays(ySel, mSel)
    d = Math.min(daysInMonth(ySel, mSel), Math.max(1, d))
    const dIdx = Math.max(0, days.indexOf(d))
    this.setData({
      showDeadlinePicker: true,
      deadlineYears: years,
      deadlineMonths: months,
      deadlineDays: days,
      deadlinePickerIdx: [yIdx, mIdx, dIdx]
    })
  },

  onDeadlinePickerViewChange(e) {
    const val = e.detail.value
    const years = this.data.deadlineYears
    const months = this.data.deadlineMonths
    const yi = val[0]
    const mi = val[1]
    let di = val[2]
    const ySel = years[yi]
    const mSel = months[mi]
    const days = buildDays(ySel, mSel)
    if (di >= days.length) di = days.length - 1
    if (di < 0) di = 0
    this.setData({
      deadlinePickerIdx: [yi, mi, di],
      deadlineDays: days
    })
  },

  confirmDeadlinePicker() {
    const [yi, mi, di] = this.data.deadlinePickerIdx
    const y = this.data.deadlineYears[yi]
    const m = this.data.deadlineMonths[mi]
    const d = this.data.deadlineDays[di]
    const deadlineDate = `${y}-${pad2(m)}-${pad2(d)}`
    this.setData({ deadlineDate, showDeadlinePicker: false })
  },

  clearDeadlinePicker() {
    this.setData({ deadlineDate: '', showDeadlinePicker: false })
  },

  cancelDeadlinePicker() {
    this.setData({ showDeadlinePicker: false })
  },

  async create() {
    const { title, target, deadlineDate } = this.data
    if (!title || !target) {
      wx.showToast({ title: '请填写名称与目标金额', icon: 'none' })
      return
    }
    const target_amount = parseFloat(target)
    if (!(target_amount > 0)) {
      wx.showToast({ title: '目标金额须大于 0', icon: 'none' })
      return
    }
    const payload = { title, target_amount, unlimited: false }
    if (deadlineDate) {
      payload.deadline_date = deadlineDate
    } else {
      payload.unlimited = true
    }
    wx.showLoading({ title: '创建中' })
    try {
      await api.createPlan(payload)
      wx.hideLoading()
      this.toggleForm()
      this.load()
      wx.showToast({ title: '已创建', icon: 'success' })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: (e && e.detail) || '创建失败', icon: 'none' })
    }
  },

  async toggleExpand(e) {
    const idx = Number(e.currentTarget.dataset.index)
    if (Number.isNaN(idx) || idx < 0 || idx >= this.data.plans.length) return
    const cur = this.data.plans[idx]
    const nextExpanded = !cur.expanded
    const plans = this.data.plans.map((p, i) =>
      i === idx ? { ...p, expanded: nextExpanded } : p
    )
    this.setData({ plans })

    if (!nextExpanded || cur.deliveriesLoaded) return

    if (!appConfig.FETCH_PLAN_DELIVERIES) {
      const settled = this.data.plans.map((p, i) =>
        i === idx ? { ...p, deliveries: [], deliveriesLoaded: true, deliveriesLoading: false } : p
      )
      this.setData({ plans: settled })
      return
    }

    const loadingPlans = this.data.plans.map((p, i) =>
      i === idx ? { ...p, deliveriesLoading: true } : p
    )
    this.setData({ plans: loadingPlans })

    try {
      const raw = await api.getPlanDeliveries(cur.id)
      const deliveries = normalizeDeliveries(raw).map((d) => ({
        ...d,
        _when: formatWhen(d.created_at || d.delivered_at || d.at)
      }))
      const merged = this.data.plans.map((p, i) =>
        i === idx
          ? {
              ...p,
              deliveries,
              deliveriesLoaded: true,
              deliveriesLoading: false
            }
          : p
      )
      this.setData({ plans: merged })
    } catch (err) {
      const merged = this.data.plans.map((p, i) =>
        i === idx
          ? { ...p, deliveries: [], deliveriesLoaded: true, deliveriesLoading: false }
          : p
      )
      this.setData({ plans: merged })
    }
  },

  openDeliver(e) {
    const id = e.currentTarget.dataset.id
    this.setData({
      showDeliver: true,
      planId: id,
      amount: '',
      note: '',
      deliverCompleteDate: '',
      deliverCompleteTime: ''
    })
  },

  closeDeliver() {
    this.setData({
      showDeliver: false,
      planId: null,
      amount: '',
      note: '',
      deliverCompleteDate: '',
      deliverCompleteTime: ''
    })
  },

  onDeliverCompleteDate(e) {
    this.setData({ deliverCompleteDate: e.detail.value })
  },

  onDeliverCompleteTime(e) {
    this.setData({ deliverCompleteTime: e.detail.value })
  },

  /** 生成存钱成功金币弹射粒子 */
  buildCoinParticles(count = 10) {
    const emojis = ['🪙', '💰', '✨', '🪙', '💎', '🪙', '✨', '🪙', '💰', '🪙']
    const particles = []
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * 360
      const dist = 80 + Math.random() * 120
      particles.push({
        emoji: emojis[i % emojis.length],
        delay: i * 0.04,
        x: Math.cos(angle * Math.PI / 180) * dist,
        y: Math.sin(angle * Math.PI / 180) * dist,
        rotate: Math.random() * 360,
      })
    }
    return particles
  },

  /** 收起金币动效 */
  onCoinEffectDone() {
    this.setData({ showCoinEffect: false, coinParticles: [] })
  },

  async doDeliver() {
    const { planId, amount, note, deliverCompleteDate, deliverCompleteTime } = this.data
    if (!planId) return
    if (!amount) {
      wx.showToast({ title: '请输入金额', icon: 'none' })
      return
    }
    const extra = {}
    if (deliverCompleteDate) {
      const t = deliverCompleteTime || '00:00'
      const segs = String(t).split(':')
      const hh = pad2(Math.min(23, Math.max(0, parseInt(segs[0], 10) || 0)))
      const mm = pad2(Math.min(59, Math.max(0, parseInt(segs[1], 10) || 0)))
      extra.completed_at = `${deliverCompleteDate} ${hh}:${mm}:00`
    }
    wx.showLoading({ title: '提交中' })
    try {
      const res = await api.deliverPlan(planId, parseFloat(amount), note || '', extra)
      wx.hideLoading()
      this.closeDeliver()
      const formatted = fmtNum(amount)
      // 振动反馈
      wx.vibrateShort({ type: 'medium' }).catch(() => {})
      // 金币弹射动画
      this.setData({
        showCoinEffect: true,
        coinParticles: this.buildCoinParticles(12),
        lastAmount: formatted,
      })
      // 1.4秒后自动关闭
      if (this._coinTimer) clearTimeout(this._coinTimer)
      this._coinTimer = setTimeout(() => {
        this._coinTimer = null
        this.setData({ showCoinEffect: false, coinParticles: [] })
      }, 1400)
      await this.load()
      if (res && res.done) {
        const donePlan = this.data.plans.find((x) => String(x.id) === String(planId))
        // 金币动效结束后弹出图腾
        setTimeout(() => {
          this.openTotemCelebrate(
            donePlan || {
              id: planId,
              title: '存钱计划',
              _curText: fmtNum(amount),
              _tarText: '—'
            },
            { closeAction: 'none' }
          )
        }, 1500)
      } else {
        wx.showToast({ title: '已记录', icon: 'success' })
      }
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: (e && e.detail) || '提交失败', icon: 'none' })
    }
  },

  async del(e) {
    const id = e.currentTarget.dataset.id
    const r = await wx.showModal({
      title: '删除计划？',
      content: '删除后存入记录也会清空'
    })
    if (!r.confirm) return
    try {
      await api.deletePlan(id)
      this.load()
    } catch (err) {
      wx.showToast({ title: '删除失败', icon: 'none' })
    }
  },

  /** 检查未读的完成祝贺 */
  checkCongratulate(plans) {
    const userInfo = wx.getStorageSync('userInfo') || {}
    const uid = String(userInfo.id)
    if (!uid) return
    for (const p of plans) {
      if (!p.done) continue
      if (!p.notify_status) continue
      try {
        const ns = JSON.parse(p.notify_status)
        if (ns[uid] === 'unread') {
          this.openTotemCelebrate(p, { closeAction: 'congratulate' })
          return
        }
      } catch(e) {}
    }
  },

  noop() {},

  openTotemCelebrate(plan, opts = {}) {
    if (!plan) return
    if (this._totemBurstTimer) {
      clearTimeout(this._totemBurstTimer)
      this._totemBurstTimer = null
    }
    const totemPlan = {
      title: plan.title || '计划',
      _curText: plan._curText != null ? plan._curText : fmtNum(plan.current_amount),
      _tarText: plan._tarText != null ? plan._tarText : fmtNum(plan.target_amount)
    }
    this.setData({
      showTotemCelebrate: true,
      totemPlan,
      totemParticles: buildTotemParticles(44, 0),
      totemCloseAction: opts.closeAction || 'none',
      totemPlanId: plan.id
    })
    this._totemBurstTimer = setTimeout(() => {
      this._totemBurstTimer = null
      if (!this.data.showTotemCelebrate) return
      this.setData({ totemParticles: buildTotemParticles(40, 1000) })
    }, 620)
  },

  async closeTotemCelebrate() {
    if (this._totemBurstTimer) {
      clearTimeout(this._totemBurstTimer)
      this._totemBurstTimer = null
    }
    const { totemCloseAction, totemPlanId } = this.data
    this.setData({
      showTotemCelebrate: false,
      totemPlan: null,
      totemParticles: [],
      totemCloseAction: 'none',
      totemPlanId: null
    })
    if (totemCloseAction === 'congratulate' && totemPlanId) {
      try {
        await api.congratulatePlan(totemPlanId)
      } catch (e) {}
      this.load()
    }
  },

  /** 阻止弹层点击冒泡 */
  catchTap() {},

  goBack() {
    wx.navigateBack()
  },

  /** 游客引导弹窗 */
  _guestPrompt() {
    wx.showModal({
      title: '💕 登录体验完整功能',
      content: '登录后可以和TA一起：共同存钱、宠物养成、纪念日提醒、每日签到',
      confirmText: '去登录',
      confirmColor: '#E8924C',
      cancelText: '暂不',
      success: (res) => {
        if (res.confirm) {
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  },
})