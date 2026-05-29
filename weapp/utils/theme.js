/** 全站固定主题 — 蜜桃苏打（年轻情侣向） */
const UI_THEME = 'bloom'

function readTheme() {
  return UI_THEME
}

/** 保留空实现，避免旧代码调用报错 */
function writeTheme() {
  return UI_THEME
}

/** 蜜桃苏打导航栏 — 主色 #FF8FAB */
const NAV_BAR_BG = '#FF8FAB'

function applyNavigationBar() {
  wx.setNavigationBarColor({
    frontColor: '#ffffff',
    backgroundColor: NAV_BAR_BG,
    animation: { duration: 200, timingFunc: 'easeIn' }
  })
}

function progressColors() {
  return {
    progressActive: '#FF6B9D',
    progressBg: 'rgba(255, 107, 157, 0.14)'
  }
}

module.exports = {
  UI_THEME,
  readTheme,
  writeTheme,
  applyNavigationBar,
  progressColors
}
