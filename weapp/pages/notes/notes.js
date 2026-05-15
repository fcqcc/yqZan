const api = require('../../utils/api')
Page({
  data: { notes: [], content: '', userInfo: null },
  onShow() {
    this.setData({ userInfo: wx.getStorageSync('userInfo') || {} })
    this.load()
  },
  async load() { try { const r = await api.getNotes(); this.setData({ notes: r.notes || [] }) } catch(e) {} },
  async send() {
    if (!this.data.content) return
    await api.createNote(this.data.content)
    this.setData({ content: '' }); this.load()
  },
  async like(e) { await api.likeNote(e.currentTarget.dataset.id); this.load() }
})