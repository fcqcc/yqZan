const api = require('../../utils/api')

const PAPER_TINTS = [
  '#faf6ef', '#f7f2e8', '#fcf9f3', '#f5efe4', '#faf8f2', '#f0ebe3'
]

function mapNote(n, i, userId) {
  const created = n.created_at != null ? String(n.created_at) : ''
  let dateShort = '--'
  if (created.length >= 10) dateShort = created.slice(5, 10)
  else if (created.length > 0) dateShort = created
  return {
    ...n,
    paper: PAPER_TINTS[i % PAPER_TINTS.length],
    dateShort,
    isMine: n.user_id === userId,
  }
}

Page({
  data: { tabBarIndex: 1, notes: [], content: '', userInfo: {}, maxLength: 200, stickId: null },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    const userInfo = wx.getStorageSync('userInfo') || {}
    this.setData({ userInfo })
    this.load()
  },

  async fetchNotes() {
    const userInfo = wx.getStorageSync('userInfo') || {}
    const r = await api.getNotes()
    return (r.notes || []).map((n, i) => mapNote(n, i, userInfo.id))
  },

  async load() {
    try {
      const notes = await this.fetchNotes()
      this.setData({ notes })
    } catch (e) {}
  },

  async send() {
    const content = this.data.content.trim()
    if (!content) return
    const oldIds = new Set((this.data.notes || []).map((n) => String(n.id)))
    wx.showLoading({ title: '贴上去...' })
    try {
      await api.createNote(content)
      const notes = await this.fetchNotes()
      const newest = notes.find((n) => !oldIds.has(String(n.id)))
      wx.hideLoading()
      if (this._stickTimer) clearTimeout(this._stickTimer)
      this._stickTimer = null
      this.setData({ content: '', notes, stickId: newest ? newest.id : null })
      this._stickTimer = setTimeout(() => {
        this.setData({ stickId: null })
        this._stickTimer = null
      }, 620)
      try { wx.vibrateShort({ type: 'light' }) } catch (e) {}
      wx.showToast({ title: '已贴上 💕', icon: 'none' })
    } catch (e) { wx.hideLoading() }
  },

  async like(e) {
    await api.likeNote(e.currentTarget.dataset.id)
    this.load()
  },

  async del(e) {
    const id = e.currentTarget.dataset.id
    const r = await wx.showModal({ title: '删除', content: '确定删除这条留言？' })
    if (!r.confirm) return
    try {
      await api.deleteNote(id)
      wx.showToast({ title: '已删除', icon: 'none' })
      this.load()
    } catch (e) { wx.showToast({ title: '删除失败', icon: 'none' }) }
  },
  uiTheme: getApp().globalData.uiTheme || 'handdrawn',
})
