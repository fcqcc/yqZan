// ===== 主题系统 =====

const THEMES = {
  bloom: {
    name: '蜜桃苏打',
    navBg: '#FF8FAB',
    navFront: '#ffffff',
  },
  handdrawn: {
    name: '可爱手绘',
    navBg: '#E891A4',
    navFront: '#ffffff',
  },
}

const DEFAULT_THEME = 'handdrawn'

function readTheme() {
  try {
    const saved = wx.getStorageSync('uiTheme')
    if (saved && THEMES[saved]) return saved
  } catch (e) {}
  return DEFAULT_THEME
}

function writeTheme(name) {
  if (!name || !THEMES[name]) return
  try {
    wx.setStorageSync('uiTheme', name)
  } catch (e) {}
}

function applyNavigationBar(themeName) {
  const t = THEMES[themeName || readTheme()]
  wx.setNavigationBarColor({
    frontColor: t.navFront,
    backgroundColor: t.navBg,
    animation: { duration: 200, timingFunc: 'easeIn' }
  })
}

function progressColors() {
  return {
    progressActive: '#E891A4',
    progressBg: 'rgba(232, 145, 164, 0.12)'
  }
}

function getThemeList() {
  return Object.entries(THEMES).map(([key, val]) => ({
    key,
    name: val.name,
    navBg: val.navBg,
  }))
}

module.exports = {
  UI_THEME: readTheme(),
  THEMES,
  readTheme,
  writeTheme,
  applyNavigationBar,
  progressColors,
  getThemeList,
}
