// app.js
// 线上版本使用域名，微信小程序要求 https
const theme = require('./utils/theme')

App({
  globalData: {
    baseUrl: 'https://yqzan.cn',
    token: '',
    userInfo: null,
    uiTheme: theme.UI_THEME
  },

  onLaunch() {
    try {
      wx.removeStorageSync('uiTheme')
    } catch (e) {}
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token) {
      this.globalData.token = token
      this.globalData.userInfo = userInfo
    }
    this.globalData.uiTheme = theme.readTheme()
  }
})
