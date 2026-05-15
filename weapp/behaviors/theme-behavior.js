const themeUtil = require('../utils/theme')

/** 注入固定主题类名，并同步导航栏与 TabBar 选中态 */
module.exports = Behavior({
  data: {
    uiTheme: themeUtil.UI_THEME
  },

  pageLifetimes: {
    show() {
      themeUtil.applyNavigationBar()
      if (typeof this.getTabBar !== 'function') return

      /** 必须用栈顶页的 tabBarIndex：首页 onShow 触发的延迟重试若闭包旧 index，会把已切到便利贴时的底栏又刷成首页高亮 */
      const readSelectedFromStack = () => {
        const pages = getCurrentPages()
        const top = pages && pages.length ? pages[pages.length - 1] : null
        if (top && typeof top.data.tabBarIndex === 'number') return top.data.tabBarIndex
        if (typeof this.data.tabBarIndex === 'number') return this.data.tabBarIndex
        return null
      }

      const sync = (n) => {
        const bar = this.getTabBar()
        if (bar) {
          const sel = readSelectedFromStack()
          if (typeof sel === 'number') bar.setData({ selected: sel })
          return
        }
        if (n < 20) setTimeout(() => sync(n + 1), 40)
      }
      sync(0)
    }
  }
})
