// app.js
App({
  globalData: {
    baseUrl: 'http://localhost:5000',  // 开发环境，上线改成服务器地址
    token: '',
    userInfo: null
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
  }
})
