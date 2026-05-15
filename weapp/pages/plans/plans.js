// pages/plans/plans.js
const api = require('../../utils/api')

Page({
  data: { plans: [], showForm: false, title: '', target: '', showDeliver: false, planId: null, amount: '', note: '' },
  onShow() { this.load() },
  async load() { try { const plans = await api.getPlans(); this.setData({ plans }) } catch(e) {} },
  toggleForm() { this.setData({ showForm: !this.data.showForm, title: '', target: '' }) },
  async create() {
    const { title, target } = this.data
    if (!title || !target) return wx.showToast({ title: '填写完整', icon: 'none' })
    wx.showLoading({ title: '创建中' })
    try { await api.createPlan({ title, target_amount: parseFloat(target) }); wx.hideLoading(); this.toggleForm(); this.load() }
    catch(e) { wx.hideLoading(); wx.showToast({ title: '失败', icon: 'none' }) }
  },
  openDeliver(e) { this.setData({ showDeliver: true, planId: e.currentTarget.dataset.id, amount: '', note: '' }) },
  closeDeliver() { this.setData({ showDeliver: false }) },
  async doDeliver() {
    const { planId, amount, note } = this.data
    if (!amount) return wx.showToast({ title: '输入金额', icon: 'none' })
    wx.showLoading({ title: '提交中' })
    try { await api.deliverPlan(planId, parseFloat(amount), note); wx.hideLoading(); this.closeDeliver(); this.load() }
    catch(e) { wx.hideLoading(); wx.showToast({ title: '失败', icon: 'none' }) }
  },
  async del(e) {
    const id = e.currentTarget.dataset.id
    const r = await wx.showModal({ title: '删除计划？', content: '删除后交付记录也会清空' })
    if (r.confirm) { await api.deletePlan(id); this.load() }
  },
  moneyFilter(v) { return (v || 0).toLocaleString() }
})