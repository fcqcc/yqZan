/**
 * 通用游客拦截行为
 *
 * 所有 Tab 页面（首页/计划/我的）引用此 behavior 后，
 * 点击底部菜单栏以外的事件，自动弹出登录确认弹窗。
 * 登录后（token 存在）自动解除拦截。
 */
module.exports = Behavior({
  data: {
    isGuest: false,
  },

  attached() {
    const token = wx.getStorageSync('token')
    this.setData({ isGuest: !token })
  },

  pageLifetimes: {
    show() {
      const token = wx.getStorageSync('token')
      this.setData({ isGuest: !token })
    }
  },

  methods: {
    /** 通用拦截：提示登录 */
    onGuestAction() {
      wx.showModal({
        title: '提示',
        content: '此功能需要登录后使用，是否前往登录？',
        confirmText: '前往登录',
        cancelText: '暂不',
        success: (res) => {
          if (res.confirm) {
            wx.reLaunch({ url: '/pages/login/login' })
          }
        }
      })
    },
  },
})
