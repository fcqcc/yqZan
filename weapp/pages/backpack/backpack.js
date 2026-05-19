// pages/backpack/backpack.js — 背包 & 图鉴
const api = require('../../utils/api')

Page({
  data: {
    tab: 'backpack',
    items: [],
    groupedItems: [],
    // 图鉴数据
    pokedexTab: 'pets',  // pets / items
    petsList: [],
    evolutionsList: [],
    itemsList: [],
    petsObtained: 0, petsTotal: 0,
    itemsObtained: 0, itemsTotal: 0,
  },

  onShow() {
    this.load()
  },

  async load() {
    try {
      const [inventoryRes, bestiaryRes] = await Promise.all([
        api.getInventory().catch(() => []),
        api.getBestiary().catch(() => ({})),
      ])

      const inventory = Array.isArray(inventoryRes) ? inventoryRes : (inventoryRes.items || [])
      const bestiary = bestiaryRes

      // 背包物品
      const marked = inventory.map(item => ({
        ...item,
        usable: item.item_type === 'consumable',
      }))
      const grouped = this.groupItems(marked)

      // 图鉴
      const petsList = (bestiary.pets || []).sort((a, b) => {
        const order = { N: 0, R: 1, SR: 2, SSR: 3, 'SSR+': 4 }
        return (order[a.rarity] || 0) - (order[b.rarity] || 0)
      })
      const evolutionsList = bestiary.evolutions || []
      const itemsList = (bestiary.items || []).sort((a, b) => {
        const order = { N: 0, R: 1, SR: 2, SSR: 3, 'SSR+': 4 }
        return (order[a.rarity] || 0) - (order[b.rarity] || 0)
      })

      const petsObtained = petsList.filter(p => p.obtained).length
      const itemsObtained = itemsList.filter(i => i.obtained).length

      this.setData({
        items: marked,
        groupedItems: grouped,
        petsList, evolutionsList, itemsList,
        petsObtained, petsTotal: petsList.length,
        itemsObtained, itemsTotal: itemsList.length,
      })
    } catch (e) { console.error('load backpack error:', e) }
  },

  // ===== TAB 切换 =====

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ tab })
  },

  switchPokedexTab(e) {
    const pokedexTab = e.currentTarget.dataset.tab
    this.setData({ pokedexTab })
  },

  // ===== 背包 =====

  groupItems(items) {
    const grouped = {}
    for (const item of items) {
      const type = item.type_display || item.item_type || '其他'
      if (!grouped[type]) grouped[type] = { type, type_display: type, list: [] }
      grouped[type].list.push(item)
    }
    const order = ['消耗品', '卡牌', '进化道具', '配饰', '背景', '其他']
    return order
      .filter(t => grouped[t])
      .map(t => grouped[t])
      .concat(Object.keys(grouped).filter(k => !order.includes(k)).map(k => grouped[k]))
  },

  typeName(type) {
    const map = {
      consumable: '消耗品',
      accessory: '配饰',
      background: '背景',
      evolution_item: '进化道具',
      other: '其他',
    }
    return map[type] || type
  },

  // ===== 使用物品 =====

  async onUseItem(e) {
    const itemId = e.currentTarget.dataset.id
    const name = e.currentTarget.dataset.name
    if (!itemId) return

    const item = this.data.items.find(i => i.id === itemId)
    if (!item || !item.usable) {
      wx.showToast({ title: '该物品无法直接使用', icon: 'none' })
      return
    }

    wx.showModal({
      title: '使用物品',
      content: `确定使用「${name || item.name}」吗？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          const result = await api.useItem(itemId)
          const msg = result.effect || result.message || '使用成功 ✨'
          wx.showToast({ title: msg, icon: 'none', duration: 2000 })
          this.load()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '使用失败', icon: 'none' })
        }
      },
    })
  },
})
