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

  /** 一键导入节日（带勾选） */
  async importHolidays() {
    wx.showLoading({ title: '加载中' })
    try {
      const list = await api.getHolidayList()
      wx.hideLoading()

      const items = list.map(h => ({
        name: `${h.emoji} ${h.title}（${h.date}）`,
        checked: !h.existing,
        disabled: h.existing,
      }))

      // 微信小程序用 picker 多选不方便，改用模态列表展示
      if (items.every(i => i.disabled)) {
        wx.showToast({ title: '所有节日已导入过了', icon: 'none' })
        return
      }

      const selected = items.filter(i => !i.disabled).map(i => {
        // 提取title: "🎊 元旦（2026-01-01）" → "元旦"
        return i.name.match(/[^ ]+ (.+)（20/)?.[1]?.replace('（）','') || ''
      }).filter(Boolean)

      if (selected.length === 0) {
        wx.showToast({ title: '没有可导入的节日', icon: 'none' })
        return
      }

      wx.showModal({
        title: '选择要导入的节日',
        content: `将添加以下 ${selected.length} 个节日：\n${selected.join('、')}`,
        cancelText: '取消',
        confirmText: '确认导入',
        success: async (res) => {
          if (!res.confirm) return
          wx.showLoading({ title: '导入中' })
          try {
            const result = await api.importHolidays(selected)
            wx.hideLoading()
            wx.showToast({ title: `✅ 成功导入${result.imported}个节日`, icon: 'none' })
            this.load()
          } catch (e) {
            wx.hideLoading()
            wx.showToast({ title: '导入失败', icon: 'none' })
          }
        }
      })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },
})