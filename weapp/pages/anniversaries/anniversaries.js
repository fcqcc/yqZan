// pages/anniversaries/anniversaries.js
const api = require('../../utils/api')
const theme = require('../../utils/theme')

function pad2(n) { return (n < 10 ? '0' : '') + n }
function daysInMonth(y, m) { return new Date(y, m, 0).getDate() }
function buildYears(y) { const a = []; for (let i = y - 2; i <= y + 10; i++) a.push(i); return a }
function buildMonths() { return [1,2,3,4,5,6,7,8,9,10,11,12] }
function buildDays(y, m) { const max = daysInMonth(y, m); const a = []; for (let i = 1; i <= max; i++) a.push(i); return a }

/** 颜色分类映射 */
const CATEGORY_MAP = [
  { key: 'festival', label: '节日', emoji: '🎉', colorClass: 'red' },
  { key: 'anniv', label: '纪念', emoji: '💑', colorClass: 'purple' },
  { key: 'birthday', label: '生日', emoji: '🎂', colorClass: 'orange' },
  { key: 'other', label: '其他', emoji: '💕', colorClass: 'green' },
]

/** 根据标题猜测分类 */
function guessCategory(title) {
  const t = title || ''
  if (/节|旦|夕|年|诞|圣诞|跨年/.test(t)) return 'festival'
  if (/生日|诞辰/.test(t)) return 'birthday'
  if (/纪念|周年|在一起|恋爱|结婚|领证|求婚|订婚/.test(t)) return 'anniv'
  return 'other'
}

Page({
  data: {
    anniversaries: [],
    filteredAnniversaries: [],
    activeCategory: '',
    categories: [],
    totalDays: 0,
    nextAnniv: null,
    showForm: false, title: '', dateVal: '',
    showDatePicker: false,
    dateYears: [], dateMonths: [], dateDays: [],
    datePickerIdx: [0, 0, 0],
    showHolidayPicker: false,
    holidayList: [],
    holidaySelectedCount: 0,
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
  },

  onLoad(options) {
    this.setData(theme.getNavLayout())
    if (options && options.date) {
      this.setData({ dateVal: options.date, showForm: true })
    }
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    this.load()
  },

  async load() {
    try {
      const anniversaries = await api.getAnniversaries()
      const now = new Date()
      const todayStr = `${now.getFullYear()}-${pad2(now.getMonth()+1)}-${pad2(now.getDate())}`

      // 计算总陪伴天数
      const sorted = anniversaries.slice().sort((a, b) => {
        const da = a.date_val ? new Date(a.date_val) : new Date()
        const db = b.date_val ? new Date(b.date_val) : new Date()
        return da - db
      })
      let totalDays = 0
      const firstDate = sorted.length > 0 ? sorted[0].date_val : null
      if (firstDate) {
        totalDays = Math.max(1, Math.round((now - new Date(firstDate)) / 86400000))
      }

      // 丰富数据：分类、天数、颜色
      const withMeta = anniversaries.map(a => {
        const p = a.date_val ? a.date_val.split('-') : []
        let days = '--', isToday = false
        if (p.length >= 3) {
          const d = new Date(now.getFullYear(), parseInt(p[1]) - 1, parseInt(p[2]))
          if (d < now) d.setFullYear(d.getFullYear() + 1)
          days = Math.ceil((d - now) / 86400000)
          isToday = a.date_val === todayStr
        }
        const catKey = guessCategory(a.title)
        const cat = CATEGORY_MAP.find(c => c.key === catKey) || CATEGORY_MAP[3]
        return {
          ...a,
          days: isToday ? 0 : days,
          isToday,
          colorClass: cat.colorClass,
          category: cat.label,
          icon: a.icon || (catKey === 'birthday' ? '🎂' : catKey === 'festival' ? '🎉' : '💑'),
          recurring: a.recurring !== false,
        }
      })

      // 按距离排序：今天排最前，其余升序
      withMeta.sort((a, b) => {
        if (a.isToday && !b.isToday) return -1
        if (!a.isToday && b.isToday) return 1
        return (a.days === '--' ? 99999 : a.days) - (b.days === '--' ? 99999 : b.days)
      })

      // 找下一个纪念日（最近一个非今天）
      const nextAnniv = withMeta.find(a => !a.isToday && a.days !== '--' && a.days > 0 && a.days < 99999) || null

      // 分类统计数据
      const categories = CATEGORY_MAP.map(c => ({
        ...c,
        count: withMeta.filter(a => guessCategory(a.title) === c.key).length,
      }))

      this.setData({
        anniversaries: withMeta,
        totalDays,
        nextAnniv,
        categories,
      })
      this.filterByCategory(this.data.activeCategory)
    } catch(e) {}
  },

  filterByCategory(catKey) {
    const { anniversaries } = this.data
    const filtered = catKey
      ? anniversaries.filter(a => guessCategory(a.title) === catKey)
      : anniversaries
    this.setData({ filteredAnniversaries: filtered })
  },

  onCategoryTap(e) {
    const cat = e.currentTarget.dataset.cat || ''
    this.setData({ activeCategory: cat })
    this.filterByCategory(cat)
  },

  toggleForm() {
    this.setData({
      showForm: !this.data.showForm,
      title: '',
      dateVal: '',
      showDatePicker: false,
    })
  },

  openDatePicker() {
    const now = new Date()
    let y = now.getFullYear(), m = now.getMonth() + 1, d = now.getDate()
    const cur = this.data.dateVal
    if (cur && /^\d{4}-\d{2}-\d{2}$/.test(cur)) {
      const p = cur.split('-').map(Number)
      y = p[0]; m = p[1]; d = p[2]
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
      showDatePicker: true,
      dateYears: years,
      dateMonths: months,
      dateDays: days,
      datePickerIdx: [yIdx, mIdx, dIdx],
    })
  },

  onDatePickerViewChange(e) {
    const val = e.detail.value
    const years = this.data.dateYears
    const months = this.data.dateMonths
    const yi = val[0], mi = val[1]
    let di = val[2]
    const ySel = years[yi]
    const mSel = months[mi]
    const days = buildDays(ySel, mSel)
    if (di >= days.length) di = days.length - 1
    if (di < 0) di = 0
    this.setData({
      datePickerIdx: [yi, mi, di],
      dateDays: days,
    })
  },

  confirmDatePicker() {
    const [yi, mi, di] = this.data.datePickerIdx
    const y = this.data.dateYears[yi]
    const m = this.data.dateMonths[mi]
    const d = this.data.dateDays[di]
    const dateVal = `${y}-${pad2(m)}-${pad2(d)}`
    this.setData({ dateVal, showDatePicker: false })
  },

  closeDatePicker() {
    this.setData({ showDatePicker: false })
  },

  async create() {
    if (!this.data.title || !this.data.dateVal) return
    await api.createAnniversary({ title: this.data.title, date_val: this.data.dateVal })
    this.toggleForm(); this.load()
  },
  catchTap() {},

  async del(e) {
    const id = e.currentTarget.dataset.id
    const title = e.currentTarget.dataset.title
    const r = await wx.showModal({ title: '删除', content: `确定删除「${title}」？` })
    if (!r.confirm) return
    try {
      await api.deleteAnniversary(id)
      wx.showToast({ title: '已删除', icon: 'none' })
      this.load()
    } catch (e) {
      wx.showToast({ title: '删除失败', icon: 'none' })
    }
  },

  async importHolidays() {
    wx.showLoading({ title: '加载中' })
    try {
      const list = await api.getHolidayList()
      wx.hideLoading()
      const holidayList = list.map(h => ({
        title: h.title, date: h.date, emoji: h.emoji,
        disabled: h.existing, checked: !h.existing,
      }))
      const count = holidayList.filter(i => i.checked && !i.disabled).length
      this.setData({ showHolidayPicker: true, holidayList, holidaySelectedCount: count })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  onHolidayCheckChange(e) {
    const checkedTitles = e.detail.value || []
    const holidayList = this.data.holidayList.map(h => ({
      ...h, checked: h.disabled ? h.checked : checkedTitles.includes(h.title),
    }))
    const count = holidayList.filter(i => i.checked && !i.disabled).length
    this.setData({ holidayList, holidaySelectedCount: count })
  },

  async confirmImport() {
    const selected = this.data.holidayList.filter(i => i.checked && !i.disabled).map(i => i.title)
    if (selected.length === 0) {
      wx.showToast({ title: '请至少选择一个节日', icon: 'none' })
      return
    }
    wx.showLoading({ title: '导入中' })
    try {
      const result = await api.importHolidays(selected)
      wx.hideLoading()
      this.setData({ showHolidayPicker: false })
      wx.showToast({ title: `✅ 成功导入${result.imported}个节日`, icon: 'none' })
      this.load()
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '导入失败', icon: 'none' })
    }
  },

  closeHolidayPicker() {
    this.setData({ showHolidayPicker: false })
  },

  goBack() {
    wx.navigateBack()
  },
})
