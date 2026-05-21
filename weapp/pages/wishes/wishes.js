// pages/wishes/wishes.js
const api = require('../../utils/api')

const STATUS_LABEL = {
  promised: '已许下',
  in_progress: '进行中',
  fulfilled: '已实现'
}

const NEXT_ACTION_LABEL = {
  promised: '开始兑现',
  in_progress: '标记完成',
  fulfilled: '重新许下'
}

function enrichWishes(list) {
  return (list || []).map((w) => ({
    ...w,
    statusLabel: STATUS_LABEL[w.status] || w.status,
    nextActionLabel: NEXT_ACTION_LABEL[w.status] || '更新进度'
  }))
}

Page({
  data: { wishes: [], showForm: false, title: '', description: '' },
  onShow() {
    this.load()
  },
  async load() {
    try {
      const raw = await api.getWishes()
      this.setData({ wishes: enrichWishes(raw) })
    } catch (e) {}
  },
  toggleForm() {
    this.setData({ showForm: !this.data.showForm, title: '', description: '' })
  },
  async create() {
    const { title, description } = this.data
    if (!title) return wx.showToast({ title: '填写心愿名称', icon: 'none' })
    wx.showLoading()
    try {
      await api.createWish({ title, description })
      wx.hideLoading()
      this.toggleForm()
      this.load()
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: '失败', icon: 'none' })
    }
  },
  async updateStatus(e) {
    const { id, status } = e.currentTarget.dataset
    const next =
      { promised: 'in_progress', in_progress: 'fulfilled', fulfilled: 'promised' }[status] || 'promised'
    await api.updateWish(id, { status: next })
    this.load()
  },
  async del(e) {
    const r = await wx.showModal({ title: '删除心愿？', content: '删除后无法恢复' })
    if (r.confirm) {
      await api.deleteWish(e.currentTarget.dataset.id)
      this.load()
    }
  },

  /** 阻止弹层点击冒泡 */
  catchTap() {}
})