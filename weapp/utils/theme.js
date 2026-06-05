// ===== 主题系统 =====

const THEMES = {
  bloom: {
    name: '蜜桃苏打',
    navBg: '#FF8FAB',
    navFront: '#ffffff',
  },
  handdrawn: {
    name: '可爱手绘',
    navBg: '#FFFFFF',
    navFront: '#000000',
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

const CUSTOM_NAV_ROUTES = new Set([
  'pages/login/login',
  'pages/home/home',
  'pages/settings/settings',
])

function getNavLayout() {
  const sys = wx.getSystemInfoSync()
  const menu = wx.getMenuButtonBoundingClientRect()
  const statusBarHeight = sys.statusBarHeight || 20
  const navBarHeight = menu.height + (menu.top - statusBarHeight) * 2
  return { statusBarHeight, navBarHeight }
}

function applyNavigationBar(themeName) {
  const pages = getCurrentPages()
  const route = pages.length ? pages[pages.length - 1].route : ''
  if (CUSTOM_NAV_ROUTES.has(route)) return

  const t = THEMES[themeName || readTheme()]
  wx.setNavigationBarColor({
    frontColor: t.navFront,
    backgroundColor: t.navBg,
    animation: { duration: 200, timingFunc: 'easeIn' },
  })
}

function progressColors() {
  return {
    progressActive: '#F9A85C',
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
  getNavLayout,
  progressColors,
  getThemeList,
}
