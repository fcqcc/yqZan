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
    showPrivacy: false, // 隐私政策弹窗
  },

  onLoad() {
    const agreed = wx.getStorageSync('privacy_agreed')
    this.setData({ showPrivacy: !agreed })
  },

  onShow() {
    // 如果已经有 token，直接跳转首页
    const token = wx.getStorageSync('token')
    if (token) {
      wx.reLaunch({ url: '/pages/home/home' })
    }
  },

  onAgreePrivacy() {
    wx.setStorageSync('privacy_agreed', true)
    this.setData({ showPrivacy: false })
  },

  onDisagreePrivacy() {
    wx.showToast({ title: '需要同意隐私政策才能使用', icon: 'none' })
  },

  onViewPrivacyPolicy() {
    // 可以链接到隐私政策页面或直接展示文本
    wx.showModal({
      title: '隐私政策',
      content: '本应用收集您的微信昵称和头像用于展示个人资料，收集您的微信openid用于识别身份。我们不会将您的个人信息分享给第三方。您同意后可以随时在设置中撤回授权。',
      showCancel: false,
      confirmText: '我知道了'
    })
  },

  onViewUserAgreement() {
    wx.showModal({
      title: '用户服务协议',
      content: '欢迎使用「一起攒」小程序。本应用仅面向已确定恋爱关系的情侣用户，提供共同存钱计划管理和宠物养成互动功能。使用本应用即表示您同意遵守相关法律法规。',
      showCancel: false,
      confirmText: '我知道了'
    })
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
