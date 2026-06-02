// app.js
// 线上版本使用域名，微信小程序要求 https
const theme = require('./utils/theme')

App({
  globalData: {
    baseUrl: 'http://127.0.0.1:5000',
    token: '',
    userInfo: null,
    uiTheme: 'handdrawn'
  },

  onLaunch() {
    theme.writeTheme('handdrawn')
    this.globalData.uiTheme = 'handdrawn'
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
    theme.applyNavigationBar('handdrawn')
  }
})
