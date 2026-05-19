const api = require('../../utils/api')
Page({
  data: { anniversaries: [], showForm: false, title: '', dateVal: '' },
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

  /** 阻止弹层点击冒泡 */
  catchTap() {},

  /** 一键导入节日 */
  async importHolidays() {
    wx.showModal({
      title: '导入节日',
      content: '一键导入2026年所有情侣节日？\n（已存在的不会重复添加）',
      success: async (res) => {
        if (!res.confirm) return
        wx.showLoading({ title: '导入中' })
        try {
          const result = await api.importHolidays()
          wx.hideLoading()
          wx.showToast({ title: `导入成功 ✨ 新增${result.imported}个节日`, icon: 'none' })
          this.load()
        } catch (e) {
          wx.hideLoading()
          wx.showToast({ title: '导入失败', icon: 'none' })
        }
      }
    })
  },
})