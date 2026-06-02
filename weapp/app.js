// app.js
// 线上版本使用域名，微信小程序要求 https
const theme = require('./utils/theme')

App({
  globalData: {
    baseUrl: 'http://127.0.0.1:5000',
    token: '',
    userInfo: null,
    uiTheme: theme.readTheme()
  },

  onLaunch() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
    // 从存储恢复主题
    const savedTheme = theme.readTheme()
    this.globalData.uiTheme = savedTheme
    theme.writeTheme(savedTheme)
  }
})
