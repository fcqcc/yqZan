// pages/anniversaries/anniversaries.js
const api = require('../../utils/api')

function pad2(n) { return (n < 10 ? '0' : '') + n }
function daysInMonth(y, m) { return new Date(y, m, 0).getDate() }
function buildYears(y) { const a = []; for (let i = y - 2; i <= y + 10; i++) a.push(i); return a }
function buildMonths() { return [1,2,3,4,5,6,7,8,9,10,11,12] }
function buildDays(y, m) { const max = daysInMonth(y, m); const a = []; for (let i = 1; i <= max; i++) a.push(i); return a }

Page({
  data: {
    anniversaries: [],
    showForm: false, title: '', dateVal: '',
    showDatePicker: false,
    dateYears: [], dateMonths: [], dateDays: [],
    datePickerIdx: [0, 0, 0],
    showHolidayPicker: false,
    holidayList: [],
    holidaySelectedCount: 0,
  },

  onShow() { this.load() },

  async load() {
    try {
      const anniversaries = await api.getAnniversaries()
      const now = new Date()
      const todayStr = `${now.getFullYear()}-${pad2(now.getMonth()+1)}-${pad2(now.getDate())}`
      const withDays = anniversaries.map(a => {
        const p = a.date_val.split('-')
        if (p.length < 3) return { ...a, days: '--', isToday: false }
        const d = new Date(now.getFullYear(), parseInt(p[1]) - 1, parseInt(p[2]))
        if (d < now) d.setFullYear(d.getFullYear() + 1)
        return {
          ...a,
          days: Math.ceil((d - now) / 86400000),
          isToday: a.date_val === todayStr,
        }
      })
      // 按距离排序：今天的排最前，其余按天数升序
      withDays.sort((a, b) => {
        if (a.isToday && !b.isToday) return -1
        if (!a.isToday && b.isToday) return 1
        return (a.days === '--' ? 99999 : a.days) - (b.days === '--' ? 99999 : b.days)
      })
      this.setData({ anniversaries: withDays })
    } catch(e) {}
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
  /** 阻止弹层点击冒泡 */
  catchTap() {},

  /** 删除纪念日 */
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

  /** 打开节日选择器 */
  async importHolidays() {
    wx.showLoading({ title: '加载中' })
    try {
      const list = await api.getHolidayList()
      wx.hideLoading()

      // 已存在的默认勾上但禁用
      const holidayList = list.map(h => ({
        title: h.title,
        date: h.date,
        emoji: h.emoji,
        disabled: h.existing,
        checked: !h.existing,
      }))
      const count = holidayList.filter(i => i.checked && !i.disabled).length
      this.setData({ showHolidayPicker: true, holidayList, holidaySelectedCount: count })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  /** checkbox-group change 事件 */
  onHolidayCheckChange(e) {
    const checkedTitles = e.detail.value || []
    const holidayList = this.data.holidayList.map(h => ({
      ...h,
      checked: h.disabled ? h.checked : checkedTitles.includes(h.title),
    }))
    const count = holidayList.filter(i => i.checked && !i.disabled).length
    this.setData({ holidayList, holidaySelectedCount: count })
  },

  /** 确认导入勾选的节日 */
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

  /** 关闭选择器 */
  closeHolidayPicker() {
    this.setData({ showHolidayPicker: false })
  },
})
