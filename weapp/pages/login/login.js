// pages/login/login.js
const api = require('../../utils/api')

Page({
  data: {
    step: '',           // '' = 展示微信登录, 'set-nickname' = 设置昵称
    nickname: '',
    loading: false,
    nicknameLoading: false,
    error: '',
    afterLoginGoBind: false,
  },

  onShow() {
    // 如果已经有 token，直接跳转首页
    const token = wx.getStorageSync('token')
    if (token) {
      wx.reLaunch({ url: '/pages/home/home' })
    }
  },

  async handleWxLogin() {
    this.setData({ loading: true, error: '' })

    try {
      // 1. 获取微信临时 code
      const loginRes = await wx.login()
      if (!loginRes || !loginRes.code) {
        throw { detail: '获取微信登录凭证失败' }
      }

      // 2. 发送 code 到后端登录
      const res = await api.wxLogin(loginRes.code)

      // 3. 保存 token
      wx.setStorageSync('token', res.access_token)
      getApp().globalData.token = res.access_token

      // 4. 保存用户信息
      const user = res.user || res
      wx.setStorageSync('userInfo', user)
      getApp().globalData.userInfo = user

      // 5. 判断是否需要设置昵称
      if (!user.has_nickname) {
        this.setData({
          step: 'set-nickname',
          loading: false
        })
      } else {
        const dest = this.data.afterLoginGoBind
          ? '/pages/settings/settings'
          : '/pages/home/home'
        this.setData({ afterLoginGoBind: false })
        wx.reLaunch({ url: dest })
      }
    } catch (e) {
      this.setData({
        error: (e && (e.detail || e.message)) || '登录失败，请重试',
        loading: false
      })
    }
  },

  async handleSetNickname() {
    const name = (this.data.nickname || '').trim()
    if (!name) {
      this.setData({ error: '请输入昵称' })
      return
    }
    this.setData({ nicknameLoading: true, error: '' })

    try {
      const user = await api.setNickname(name)
      wx.setStorageSync('userInfo', user)
      getApp().globalData.userInfo = user
      const dest = this.data.afterLoginGoBind
        ? '/pages/settings/settings'
        : '/pages/home/home'
      this.setData({ afterLoginGoBind: false })
      wx.reLaunch({ url: dest })
    } catch (e) {
      this.setData({
        error: (e && (e.detail || e.message)) || '设置昵称失败',
        nicknameLoading: false
      })
    }
  },

  goBindPartner() {
    const token = wx.getStorageSync('token')
    if (token) {
      wx.reLaunch({ url: '/pages/settings/settings' })
      return
    }
    this.setData({ afterLoginGoBind: true })
    wx.showToast({ title: '请先完成微信登录', icon: 'none' })
  },
})
