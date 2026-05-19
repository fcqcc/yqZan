// pages/anniversaries/anniversaries.js
const api = require('../../utils/api')
Page({
  data: {
    anniversaries: [],
    showForm: false, title: '', dateVal: '',
    showHolidayPicker: false,
    holidayList: [],
    holidaySelectedCount: 0,
  },

  onShow() { this.load() },

  async load() {
    try {
      const anniversaries = await api.getAnniversaries()
      const now = new Date()
      const withDays = anniversaries.map(a => {
        const p = a.date_val.split('-')
        if (p.length < 3) return { ...a, days: '--' }
        const d = new Date(now.getFullYear(), parseInt(p[1]) - 1, parseInt(p[2]))
        if (d < now) d.setFullYear(d.getFullYear() + 1)
        return { ...a, days: Math.ceil((d - now) / 86400000) }
      })
      this.setData({ anniversaries: withDays })
    } catch(e) {}
  },

  toggleForm() { this.setData({ showForm: !this.data.showForm, title: '', dateVal: '' }) },
  onDateChange(e) { this.setData({ dateVal: e.detail.value }) },

  async create() {
    if (!this.data.title || !this.data.dateVal) return
    await api.createAnniversary({ title: this.data.title, date_val: this.data.dateVal })
    this.toggleForm(); this.load()
  },

  catchTap() {},

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

  /** 切换勾选 */
  toggleHoliday(e) {
    const idx = e.currentTarget.dataset.index
    const item = this.data.holidayList[idx]
    if (item.disabled) return
    item.checked = !item.checked
    const count = this.data.holidayList.filter(i => i.checked && !i.disabled).length
    this.setData({ holidayList: this.data.holidayList, holidaySelectedCount: count })
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
