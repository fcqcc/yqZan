// pages/wishes/wishes.js
const api = require('../../utils/api')

Page({
  data: { wishes: [], showForm: false, title: '', description: '' },
  onShow() { this.load() },
  async load() { try { const wishes = await api.getWishes(); this.setData({ wishes }) } catch(e) {} },
  toggleForm() { this.setData({ showForm: !this.data.showForm, title: '', description: '' }) },
  async create() {
    const { title, description } = this.data
    if (!title) return wx.showToast({ title: '填写心愿名称', icon: 'none' })
    wx.showLoading()
    try { await api.createWish({ title, description }); wx.hideLoading(); this.toggleForm(); this.load() }
    catch(e) { wx.hideLoading(); wx.showToast({ title: '失败', icon: 'none' }) }
  },
  async updateStatus(e) {
    const { id, status } = e.currentTarget.dataset
    const next = { promised: 'in_progress', in_progress: 'fulfilled', fulfilled: 'promised' }[status] || 'promised'
    await api.updateWish(id, { status: next })
    this.load()
  },
  async del(e) {
    const r = await wx.showModal({ title: '删除心愿？', content: '' })
    if (r.confirm) { await api.deleteWish(e.currentTarget.dataset.id); this.load() }
  }
})