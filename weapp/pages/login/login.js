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
    showLoginTerms: false,  // 合并的条款弹窗（隐私 + 登录同意）
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
    bgLoaded: false,    // 封面背景是否加载成功
    bgFailed: false,    // 封面背景加载失败
    bgImageUrl: '',     // 封面背景地址
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    // 已经有 token → 正常进入首页
    const token = wx.getStorageSync('token')
    if (token) {
      wx.reLaunch({ url: '/pages/home/home' })
    }
    // 加载封面背景（只尝试一次，不重复请求）
    if (!this.data.bgLoaded && !this.data.bgFailed) {
      this.loadBgImage()
    }
  },

  /** 尝试加载封面背景图，失败则回退渐变背景 */
  loadBgImage() {
    const baseUrl = getApp().globalData.baseUrl || 'https://yqzan.cn'
    const url = baseUrl + '/assets/images/login-bg.png'
    this.setData({ bgImageUrl: url })
    wx.getImageInfo({
      src: url,
      success: () => {
        this.setData({ bgLoaded: true })
      },
      fail: () => {
        this.setData({ bgFailed: true })
      }
    })
  },

  /** 点击「微信一键登录」→ 先弹出合并条款，同意后才调微信登录 */
  async handleWxLogin() {
    const loginTermsAgreed = wx.getStorageSync('login_terms_agreed')
    if (!loginTermsAgreed) {
      this.setData({ showLoginTerms: true })
      return
    }
    await this.doWxLogin()
  },

  /** 合并条款弹窗：同意 → 执行登录，同时标记隐私已同意 */
  onAgreeLoginTerms() {
    wx.setStorageSync('login_terms_agreed', true)
    wx.setStorageSync('privacy_agreed', true)
    this.setData({ showLoginTerms: false })
    this.doWxLogin()
  },

  onDisagreeLoginTerms() {
    this.setData({ showLoginTerms: false })
    wx.showToast({ title: '需要同意条款才能使用微信登录', icon: 'none' })
  },

  onViewLoginPrivacyPolicy() {
    wx.showModal({
      title: '隐私政策',
      content: '本应用收集您的微信昵称和头像用于展示个人资料，收集您的微信openid用于识别身份。我们不会将您的个人信息分享给第三方。您同意后可以随时在设置中撤回授权。',
      showCancel: false,
      confirmText: '我知道了'
    })
  },

  onViewLoginUserAgreement() {
    wx.showModal({
      title: '用户服务协议',
      content: '欢迎使用「一起攒」小程序。本应用仅面向已确定恋爱关系的情侣用户，提供共同存钱计划管理和宠物养成互动功能。使用本应用即表示您同意遵守相关法律法规。',
      showCancel: false,
      confirmText: '我知道了'
    })
  },

  /** 实际执行微信登录 */
  async doWxLogin() {
    this.setData({ loading: true, error: '' })

    try {
      const loginRes = await wx.login()
      if (!loginRes || !loginRes.code) {
        throw { detail: '获取微信登录凭证失败' }
      }

      const res = await api.wxLogin(loginRes.code)

      wx.setStorageSync('token', res.access_token)
      getApp().globalData.token = res.access_token

      const user = res.user || res
      wx.setStorageSync('userInfo', user)
      getApp().globalData.userInfo = user

      if (!user.has_nickname) {
        this.setData({ step: 'set-nickname', loading: false })
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

  /** 审核体验入口：连续点击标题5次触发 */
  onTitleTap() {
    const cnt = (this.data._titleTapCount || 0) + 1
    this.setData({ _titleTapCount: cnt })
    if (cnt >= 5) {
      this.setData({ _titleTapCount: 0 })
      this.doReviewLogin()
    }
  },

  /** 审核体验模式：跳过微信登录，使用模拟账号 */
  async doReviewLogin() {
    this.setData({ loading: true, error: '' })
    try {
      // 生成模拟 token 和用户信息
      const mockUser = {
        id: 99999,
        nickname: '审核员',
        has_nickname: true,
        invite_code: 'REVIEW',
        couple_id: null,
        created_at: new Date().toISOString()
      }
      // 用后端真实登录接口获取 token（后端 mock 模式已启用）
      const loginRes = await wx.login()
      let res
      if (loginRes && loginRes.code) {
        res = await api.wxLogin(loginRes.code)
      }
      const token = res && res.access_token ? res.access_token : 'mock_review_token_' + Date.now()
      const user = (res && (res.user || res)) || mockUser

      wx.setStorageSync('token', token)
      getApp().globalData.token = token
      wx.setStorageSync('userInfo', user)
      getApp().globalData.userInfo = user
      wx.setStorageSync('privacy_agreed', true)
      wx.setStorageSync('login_terms_agreed', true)

      wx.reLaunch({ url: '/pages/home/home' })
    } catch (e) {
      this.setData({
        error: (e && (e.detail || e.message)) || '体验模式登录失败',
        loading: false
      })
    }
  },
})
