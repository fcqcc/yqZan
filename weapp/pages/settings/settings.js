// pages/settings/settings.js
const api = require('../../utils/api')

Page({
  data: { userInfo: null, partner: null, inviteCode: '' },
  onShow() {
    const userInfo = wx.getStorageSync('userInfo') || {}
    this.setData({ userInfo })
    this.loadPartner()
  },
  async loadPartner() {
    try {
      const partner = await api.getPartner()
      this.setData({ partner })
    } catch (e) { this.setData({ partner: null }) }
  },
  async handleBind() {
    if (!this.data.inviteCode) return wx.showToast({ title: '请输入邀请码', icon: 'none' })
    wx.showLoading({ title: '绑定中' })
    try {
      const res = await api.bindPartner(this.data.inviteCode)
      wx.hideLoading()
      wx.showToast({ title: '绑定成功 ' + res.partner, icon: 'success' })
      this.setData({ inviteCode: '' })
      this.loadPartner()
      wx.switchTab({ url: '/pages/home/home' })
    } catch (e) { wx.hideLoading(); wx.showToast({ title: e.detail || '绑定失败', icon: 'none' }) }
  },
  async handleUnbind() {
    const r = await wx.showModal({ title: '确认解绑？', content: '解绑后数据将归档' })
    if (!r.confirm) return
    try { await api.unbindPartner(); wx.showToast({ title: '已解绑', icon: 'success' }); this.setData({ partner: null }) }
    catch (e) { wx.showToast({ title: '操作失败', icon: 'none' }) }
  },
  handleLogout() {
    wx.removeStorageSync('token'); wx.removeStorageSync('userInfo')
    getApp().globalData.token = ''; getApp().globalData.userInfo = null
    wx.reLaunch({ url: '/pages/login/login' })
  },
  copyCode() { wx.setClipboardData({ data: this.data.userInfo.invite_code }) }
})