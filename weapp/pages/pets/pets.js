// pages/pets/pets.js — 宠物管理
const api = require('../../utils/api')

Page({
  data: {
    pets: [],
    activePet: null,
    intimacyPct: 0,
    forms: [],
    canEvolve: false,
    inventory: []
  },

  onShow() {
    this.load()
  },

  async load() {
    try {
      const [petsRes, inventory] = await Promise.all([
        api.getPets().catch(() => ({ pets: [], active_pet: null })),
        api.getInventory().catch(() => [])
      ])

      const pets = petsRes.pets || []
      const activePet = petsRes.active_pet || null
      const intimacyPct = activePet && activePet.intimacy_max
        ? Math.min(100, (activePet.intimacy / activePet.intimacy_max) * 100)
        : 0

      // 构建形态列表（从所有宠物中提取已解锁的形态）
      const forms = this.buildForms(pets, activePet)

      // 判断是否可以进化（背包中有进化道具）
      const items = Array.isArray(inventory) ? inventory : (inventory.items || [])
      const canEvolve = items.some(item => (item.type === 'evolve' || item.type === 'evolution'))

      this.setData({ pets, activePet, intimacyPct, forms, canEvolve, inventory: items })
    } catch (e) { console.error('load pets error:', e) }
  },

  /**
   * 从宠物数据中构建形态列表
   * 假设宠物数据结构中有 forms 字段，或者从宠物列表推断
   */
  buildForms(pets, activePet) {
    if (!pets || pets.length === 0) return []

    // 尝试从 activePet.forms 获取
    if (activePet && activePet.forms && activePet.forms.length > 0) {
      return activePet.forms.map(f => ({
        ...f,
        unlocked: true
      }))
    }

    // 否则从宠物列表推断
    const formMap = new Map()
    for (const pet of pets) {
      const key = pet.form || pet.form_type || 'default'
      if (!formMap.has(key)) {
        formMap.set(key, {
          form: key,
          name: pet.formName || this.formLabel(key),
          emoji: pet.emoji || '🐱',
          unlocked: true
        })
      }
    }
    return Array.from(formMap.values())
  },

  /** 格式化形态显示名 */
  formLabel(form) {
    const map = {
      default: '初始形态',
      baby: '幼年体',
      child: '成长期',
      adult: '成熟体',
      evolved_1: '进化Ⅰ',
      evolved_2: '进化Ⅱ',
      evolved_3: '进化Ⅲ',
      super: '超级形态',
      ultimate: '究极体'
    }
    return map[form] || form
  },

  /** 切换活跃宠物 */
  async onSwitchPet(e) {
    const petId = e.currentTarget.dataset.id
    if (!petId) return
    try {
      await api.switchPet(petId)
      wx.showToast({ title: '切换成功', icon: 'success' })
      this.load()
    } catch (e) {
      wx.showToast({ title: e.errMsg || '切换失败', icon: 'none' })
    }
  },

  /** 切换宠物形态 */
  async onSwitchForm(e) {
    const form = e.currentTarget.dataset.form
    const activePet = this.data.activePet
    if (!activePet || !form || form === activePet.form) return
    try {
      await api.switchPetForm(activePet.id, form)
      wx.showToast({ title: '形态切换成功', icon: 'success' })
      this.load()
    } catch (e) {
      wx.showToast({ title: e.errMsg || '切换失败', icon: 'none' })
    }
  },

  /** 喂食宠物 */
  async onFeed() {
    const pet = this.data.activePet
    if (!pet) return
    try {
      await api.feedPet(pet.id)
      wx.showToast({ title: '喂食成功 ❤️', icon: 'success' })
      this.load()
    } catch (e) {
      wx.showToast({ title: e.errMsg || '喂食失败', icon: 'none' })
    }
  },

  /** 进化宠物 */
  async onEvolve() {
    const pet = this.data.activePet
    if (!pet) return

    // 找到背包中的进化道具
    const evolveItem = this.data.inventory.find(item =>
      item.type === 'evolve' || item.type === 'evolution'
    )
    if (!evolveItem) {
      wx.showToast({ title: '没有进化道具', icon: 'none' })
      return
    }

    wx.showModal({
      title: '确认进化',
      content: `消耗 1 个「${evolveItem.name || '进化道具'}」，进化 ${pet.name}？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.evolvePet(pet.id, evolveItem.inventory_id || evolveItem.id)
          wx.showToast({ title: '进化成功 ✨', icon: 'success' })
          this.load()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '进化失败', icon: 'none' })
        }
      }
    })
  }
})
