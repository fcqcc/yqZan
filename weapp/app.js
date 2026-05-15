// app.js
// baseUrl：开发者工具可用 localhost；真机预览请改为电脑局域网 IP；上线须 https 合法域名。
const theme = require('./utils/theme')

App({
  globalData: {
    baseUrl: 'http://localhost:5000',
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
