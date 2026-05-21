// pages/pets/pets.js — 宠物管理
const api = require('../../utils/api')

function getFullImageUrl(path) {
  if (!path) return ''
  return getApp().globalData.baseUrl + path
}

/** 宠物类型 → 进化道具 ID 映射 */
const EVOLUTION_ITEM_FOR_PET = {
  star_fox: 'star_ribbon',
  bamboo_dragon: 'bamboo_sword',
  wave_cat: 'sea_crown',
  honey_bear: 'rainbow_cape',
}

Page({
  data: {
    pets: [],
    activePet: null,
    intimacyPct: 0,
    forms: [],
    canEvolve: false,
    inventory: [],
    intimacyStageName: '初识',
    intimacyStageDesc: '',
    petCatalog: null,  // 后端获取的宠物配置
    petHappyClass: '',  // 互动动画class
    lastInteractTime: 0,  // 防抖时间戳
  },

  onShow() {
    this.load()
    this.loadCatalog()
  },

  async loadCatalog() {
    try {
      const cat = await api.getPetCatalog()
      this.setData({ petCatalog: cat.pet_types || [] })
    } catch (e) {}
  },

  async load() {
    try {
      const [petsRes, inventory] = await Promise.all([
        api.getPets().catch(() => ({ pets: [], active_pet: null })),
        api.getInventory().catch(() => [])
      ])

      const petsArr = Array.isArray(petsRes) ? petsRes : (petsRes.pets || [])
      const activePetFromApi = Array.isArray(petsRes) ? null : (petsRes.active_pet || null)

      const pets = petsArr.map(p => ({
        ...p,
        active: p.is_active,
        full_image_url: getFullImageUrl(p.image_url),
      }))
      let activePet = activePetFromApi
        ? { ...activePetFromApi, full_image_url: getFullImageUrl(activePetFromApi.image_url) }
        : null
      if (!activePet) {
        activePet = pets.find(p => p.is_active) || pets[0] || null
      }
      const intimacyPct = activePet ? Math.min(100, Math.round(activePet.intimacy || 0)) : 0

      // 构建形态列表（从所有宠物中提取已解锁的形态）
      const forms = this.buildForms(pets, activePet)

      // 判断是否可以进化：仅 SSR 且当前形态为 adult（第三形态）
      const items = Array.isArray(inventory) ? inventory : (inventory.items || [])
      const canEvolve = activePet
        && activePet.rarity === 'SSR'
        && activePet.form === 'adult'
        && items.some(item => item.item_type === 'evolution_item')

      // 计算亲密度阶段
      let stageName = '初识'
      let stageDesc = '继续培养感情吧～'
      if (activePet) {
        const lvl = activePet.intimacy_level || ''
        if (lvl === 'low') { stageName = '初识🤝'; stageDesc = '还有点陌生，多互动会慢慢熟悉' }
        else if (lvl === 'normal') { stageName = '熟悉😊'; stageDesc = '已经开始依赖你了，继续保持' }
        else if (lvl === 'happy') { stageName = '亲密🥰'; stageDesc = '你们之间有了深厚的感情' }
        else if (lvl === 'love') { stageName = '挚爱💕'; stageDesc = '心意相通，默契无间！' }
      }

      this.setData({ pets, activePet, intimacyPct, forms, canEvolve, inventory: items, intimacyStageName: stageName, intimacyStageDesc: stageDesc })
    } catch (e) { console.error('load pets error:', e) }
  },

  /**
   * 从宠物数据中构建形态列表
   * 假设宠物数据结构中有 forms 字段，或者从宠物列表推断
   */
  buildForms(pets, activePet) {
    if (!pets || pets.length === 0) return []
    const catalog = this.data.petCatalog || []
    if (activePet && activePet.unlocked_forms && activePet.unlocked_forms.length > 0) {
      const forms = activePet.unlocked_forms
      // 从 catalog 查找对应的形态数据
      const typeCfg = catalog.find(c => c.type === activePet.pet_type)
      const formNames = {}
      const formEmojis = {}
      if (typeCfg) {
        for (const f of typeCfg.forms) {
          formNames[f.form] = f.name
          formEmojis[f.form] = f.emoji
        }
      }
      return forms.map(f => {
        let name = formNames[f] || '未知形态'
        let emoji = formEmojis[f] || activePet.emoji || '🐾'
        // 分支进化形态从 evolutions 获取
        if (f.startsWith('branch_')) {
          const itemId = f.replace('branch_', '')
          if (typeCfg) {
            const evo = typeCfg.evolutions.find(e => e.item_id === itemId)
            if (evo) {
              name = evo.form_label
              emoji = evo.display_emoji
            }
          }
        }
        return { form: f, name, emoji, unlocked: true }
      })
    }
    return pets.map(p => ({
      form: p.current_form || 'baby',
      name: p.form_label || p.current_form,
      emoji: p.emoji || '🐾',
      unlocked: true,
    }))
  },

  /** 格式化形态显示名 */
  formLabel(form) {
    // 已废弃，保留兼容
    return form
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
      wx.showToast({ title: e.detail || e.errMsg || '切换失败', icon: 'none' })
    }
  },

  /** 切换宠物形态 */
  async onSwitchForm(e) {
    const form = e.currentTarget.dataset.form
    const activePet = this.data.activePet
    if (!activePet || !form || form === activePet.current_form) return
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
      const msg = e._statusCode === 429 ? (e.detail || '今天已经喂过了') : (e.detail || e.errMsg || '喂食失败')
      wx.showToast({ title: msg, icon: 'none' })
    }
  },

  /** 进化宠物 */
  async onEvolve() {
    const pet = this.data.activePet
    if (!pet) return

    // 找到对应宠物类型的进化道具
    const expectedItemId = EVOLUTION_ITEM_FOR_PET[pet.pet_type]
    if (!expectedItemId) {
      wx.showToast({ title: '该宠物无法进化', icon: 'none' })
      return
    }
    const evolveItem = this.data.inventory.find(item =>
      item.item_type === 'evolution_item' && item.item_id === expectedItemId
    )
    if (!evolveItem) {
      wx.showToast({ title: '没有对应的进化道具', icon: 'none' })
      return
    }

    wx.showModal({
      title: '确认进化',
      content: `消耗 1 个「${evolveItem.name || '进化道具'}」，进化 ${pet.form_label || '宠物'}？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.evolvePet(pet.id, evolveItem.item_id)
          wx.showToast({ title: '进化成功 ✨', icon: 'success' })
          this.load()
        } catch (e) {
          wx.showToast({ title: e.detail || e.errMsg || '进化失败', icon: 'none' })
        }
      }
    })
  },
  /** 点击宠物卡片→跳跃动画+抚摸API（防抖1秒） */
  onPetTap() {
    const pet = this.data.activePet
    if (!pet) return
    const now = Date.now()
    if (now - this.data.lastInteractTime < 1000) {
      wx.showToast({ title: '🔄 等一等…', icon: 'none' })
      return
    }
    this.setData({ petHappyClass: 'pet-happy', lastInteractTime: now })
    api.petPet(pet.id).catch(() => {})
    setTimeout(() => { this.setData({ petHappyClass: '' }) }, 600)
  },
})
