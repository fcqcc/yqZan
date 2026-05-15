Component({
  data: {
    selected: 0,
    tabs: [
      { pagePath: '/pages/home/home', text: '首页', icon: '/images/tab_home.png', iconActive: '/images/tab_home_active.png' },
      { pagePath: '/pages/notes/notes', text: '便利贴', icon: '/images/tab_note.png', iconActive: '/images/tab_note_active.png' },
      { pagePath: '/pages/settings/settings', text: '我的', icon: '/images/tab_me.png', iconActive: '/images/tab_me_active.png' }
    ]
  },
  methods: {
    /** 用 touchstart 而非 tap：tap 会多等一轮「抬起+点击判定」，底栏体感更钝 */
    onTabTouchStart(e) {
      const idx = Number(e.currentTarget.dataset.index)
      if (Number.isNaN(idx) || idx < 0 || idx >= this.data.tabs.length) return
      let path = this.data.tabs[idx].pagePath || ''
      if (path && !path.startsWith('/')) path = '/' + path
      const prev = Number(this.data.selected) || 0
      if (idx !== prev) this.setData({ selected: idx })
      wx.switchTab({
        url: path,
        fail: () => {
          if (idx !== prev) this.setData({ selected: prev })
        }
      })
    }
  }
})
