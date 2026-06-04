const TAB_PAGES = new Set([
  '/pages/home/home',
  '/pages/plans/plans',
  '/pages/settings/settings',
])

function openPage(url) {
  if (!url) {
    wx.showToast({ title: '页面地址无效', icon: 'none' })
    return
  }
  const path = url.split('?')[0]
  const onFail = (err) => {
    const msg = (err && err.errMsg) || '无法打开页面'
    console.error('[nav]', url, err)
    if (/not found|未找到|不存在/i.test(msg)) {
      wx.showToast({ title: '页面未注册，请重新编译', icon: 'none' })
      return
    }
    if (/limit|webview count/i.test(msg)) {
      wx.showToast({ title: '页面打开过多，请返回后再试', icon: 'none' })
      return
    }
    wx.showToast({ title: msg, icon: 'none', duration: 2500 })
  }
  if (TAB_PAGES.has(path)) {
    wx.switchTab({ url: path, fail: onFail })
  } else {
    wx.navigateTo({ url, fail: onFail })
  }
}

module.exports = { openPage }
