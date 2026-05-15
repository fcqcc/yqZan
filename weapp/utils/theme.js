/** 全站固定主题 — 偏粉实色（无毛玻璃） */
const UI_THEME = 'bloom'

function readTheme() {
  return UI_THEME
}

/** 保留空实现，避免旧代码调用报错 */
function writeTheme() {
  return UI_THEME
}

/** 与页面粉调顶栏一致 */
const NAV_BAR_BG = '#FFECF4'

function applyNavigationBar() {
  wx.setNavigationBarColor({
    frontColor: '#000000',
    backgroundColor: NAV_BAR_BG,
    animation: { duration: 200, timingFunc: 'easeIn' }
  })
}

function progressColors() {
  return {
    progressActive: '#D65C8A',
    progressBg: 'rgba(214, 92, 138, 0.16)'
  }
}

module.exports = {
  UI_THEME,
  readTheme,
  writeTheme,
  applyNavigationBar,
  progressColors
}
