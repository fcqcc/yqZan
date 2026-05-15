/**
 * 图标：使用 /images/icons/{{name}}.svg
 */
function iconPath(name) {
  const n = (name || 'star').trim()
  return `/images/icons/${n}.svg`
}

Component({
  properties: {
    name: { type: String, value: 'star' },
    size: { type: Number, value: 40 }
  },
  data: {
    iconSrc: '/images/icons/star.svg'
  },
  observers: {
    name(n) {
      this.setData({ iconSrc: iconPath(n) })
    }
  },
  lifetimes: {
    attached() {
      const n = this.properties.name != null ? this.properties.name : 'star'
      this.setData({ iconSrc: iconPath(String(n)) })
    }
  }
})
