// pages/login/login.js
const api = require('../../utils/api')

Page({
  data: { nickname: '', password: '', mode: 'login', loading: false, error: '' },

  switchMode() {
    this.setData({ mode: this.data.mode === 'login' ? 'register' : 'login', error: '' })
  },

  async handleLogin() {
    const { nickname, password, mode } = this.data
    if (!nickname || !password) { this.setData({ error: '请填写完整' }); return }
    this.setData({ loading: true, error: '' })

    try {
      const res = mode === 'login'
        ? await api.login({ user_id: nickname, password })
        : await api.register({ nickname, password })

      wx.setStorageSync('token', res.access_token)
      wx.setStorageSync('userInfo', res.user)
      getApp().globalData.token = res.access_token
      getApp().globalData.userInfo = res.user

      wx.reLaunch({ url: '/pages/home/home' })
    } catch (e) {
      this.setData({ error: e.detail || '操作失败' })
    } finally {
      this.setData({ loading: false })
    }
  }
})
