const api = require('../../utils/api')
Page({
  data: { cards: [], templates: [], showTpl: false },
  onShow() { this.loadCards() },
  async loadCards() { try { const r = await api.getCards(); this.setData({ cards: r.cards || [] }) } catch(e) {} },
  async showTemplates() {
    try { const tpl = await api.getCardTemplates(); this.setData({ templates: tpl, showTpl: true }) }
    catch(e) { wx.showToast({ title: '加载失败', icon: 'none' }) }
  },
  hideTemplates() { this.setData({ showTpl: false }) },
  async generate(e) {
    const { id, name } = e.currentTarget.dataset
    wx.showLoading({ title: '生成中' })
    try {
      await api.generateCard({ template_id: id, title: name, trigger_event: 'manual' })
      wx.hideLoading(); this.hideTemplates(); this.loadCards()
      wx.showToast({ title: '贺卡已生成' })
    } catch(e) { wx.hideLoading(); wx.showToast({ title: '生成失败', icon: 'none' }) }
  }
})