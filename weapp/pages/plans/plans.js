// pages/plans/plans.js
let api = require('../../utils/api')
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

function wrapPlan(p) {
  const cur = Number(p.current_amount) || 0
  const tar = Math.max(Number(p.target_amount) || 1, 1)
  const hasEmbed = p != null && Object.prototype.hasOwnProperty.call(p, 'deliveries')
  const embedList = hasEmbed ? normalizeDeliveries(p.deliveries) : []
  const deliveries = embedList.map((d) => ({
    ...d,
    _when: formatWhen(d.created_at || d.delivered_at || d.at)
  }))
  return {
    ...p,
    expanded: false,
    deliveries,
    deliveriesLoaded: hasEmbed,
    deliveriesLoading: false,
    progressPct: Math.min(100, (cur / tar) * 100),
    _curText: fmtNum(cur),
    _tarText: fmtNum(tar)
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
    deliverCompleteTime: ''
  },

  onShow() {
    this.load()
  },

  async load() {
    try {
      const raw = await api.getPlans()
      const list = Array.isArray(raw) ? raw : []
      const plans = list.map(wrapPlan)
      this.setData({ plans })
      this.checkCongratulate(plans)
    } catch (e) {
      this.setData({ plans: [] })
    }
  },

  toggleForm() {
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
      await this.load()
      if (res && res.done) {
        wx.showModal({
          title: '🎉 目标达成！',
          content: '太棒了！你们的目标已经完成！一起庆祝吧 🥳',
          confirmText: '耶！'
        })
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
          wx.showModal({
            title: '🎉 目标达成！',
            content: `「${p.title}」已完成！共同努力的结果 💪`,
            confirmText: '太好了！',
            success: async () => {
              try { await api.congratulatePlan(p.id); this.load() } catch(e) {}
            }
          })
          return
        }
      } catch(e) {}
    }
  },

  /** 阻止弹层点击冒泡 */
  catchTap() {}
})