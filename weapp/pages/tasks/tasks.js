// pages/tasks/tasks.js
const api = require('../../utils/api')

Page({
  data: {
    tasks: [], events: [], partner: null,
    taskTitle: '', categories: ['生活', '学习', '运动', '浪漫', '其他'], cateIdx: 0,
    statusMap: { pending: '待接受', accepted: '进行中', verified: '已完成', declined: '已拒绝' },
    myId: 0
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo') || {}
    this.setData({ myId: userInfo.id })
    this.load()
  },

  async load() {
    try {
      const [tasks, events, partner] = await Promise.all([
        api.getTasks().catch(() => []),
        api.getTaskEvents().catch(() => []),
        api.getPartner().catch(() => null)
      ])
      this.setData({ tasks, events, partner })
    } catch(e) { console.error(e) }
  },

  onCategory(e) { this.setData({ cateIdx: e.detail.value }) },

  async assignTask() {
    if (!this.data.taskTitle || !this.data.partner) return
    const map = { 0: 'life', 1: 'study', 2: 'sport', 3: 'romance', 4: 'other' }
    wx.showLoading({ title: '指派中' })
    try {
      await api.createTask({
        assignee_id: this.data.partner.id,
        title: this.data.taskTitle,
        category: map[this.data.cateIdx]
      })
      wx.hideLoading()
      this.setData({ taskTitle: '' })
      wx.showToast({ title: '已指派' })
      this.load()
    } catch(e) { wx.hideLoading(); wx.showToast({ title: '失败', icon: 'none' }) }
  },

  async acceptEvent(e) {
    const code = e.currentTarget.dataset.code
    wx.showLoading({ title: '接取中' })
    try {
      await api.acceptTaskEvent(code)
      wx.hideLoading()
      wx.showToast({ title: '已接取挑战' })
      this.load()
    } catch(e) { wx.hideLoading(); wx.showToast({ title: '失败', icon: 'none' }) }
  }
})
