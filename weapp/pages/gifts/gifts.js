const api = require('../../utils/api')
Page({
  data: { gifts: [], showForm: false, name: '', price: '', note: '' },
  onShow() { this.load() },
  async load() { try { const gifts = await api.getGifts(); this.setData({ gifts }) } catch(e) {} },
  toggleForm() { this.setData({ showForm: !this.data.showForm, name: '', price: '', note: '' }) },
  async create() {
    if (!this.data.name) return
    await api.createGift({ name: this.data.name, price: parseFloat(this.data.price) || 0, note: this.data.note })
    this.toggleForm(); this.load()
  }
})