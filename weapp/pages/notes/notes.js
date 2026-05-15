const api = require('../../utils/api')

const NOTE_COLORS = [
  'linear-gradient(135deg,#fce4ec,#f8bbd0)',
  'linear-gradient(135deg,#fff3e0,#ffccbc)',
  'linear-gradient(135deg,#e8f5e9,#c8e6c9)',
  'linear-gradient(135deg,#e3f2fd,#bbdefb)',
  'linear-gradient(135deg,#f3e5f5,#e1bee7)',
  'linear-gradient(135deg,#fff8e1,#fff9c4)',
]

Page({
  data: { notes: [], content: '', userInfo: null, maxLength: 200 },

  onShow() {
    this.setData({ userInfo: wx.getStorageSync('userInfo') || {} })
    this.load()
  },

  async load() {
    try {
      const r = await api.getNotes()
      const notes = (r.notes || []).map((n, i) => ({
        ...n,
        color: NOTE_COLORS[i % NOTE_COLORS.length]
      }))
      this.setData({ notes })
    } catch(e) {}
  },

  async send() {
    const content = this.data.content.trim()
    if (!content) return
    wx.showLoading({ title: '贴上去...' })
    try {
      await api.createNote(content)
      wx.hideLoading()
      this.setData({ content: '' })
      wx.showToast({ title: '已贴上 💕', icon: 'none' })
      this.load()
    } catch(e) { wx.hideLoading() }
  },

  async like(e) {
    await api.likeNote(e.currentTarget.dataset.id)
    this.load()
  }
})
