// pages/decision/decision.js — 情侣抽签小助手
const TUBE_TEMPLATES = {
  preset: [
    { id: 'eat', name: '今天吃什么', icon: '🍜', color: 'pink',
      options: ['火锅', '烧烤', '日料', '西餐', '冒菜', '麻辣烫', '炸鸡', '漂亮饭','小吃'] },
    { id: 'play', name: '去哪儿玩', icon: '🎡', color: 'blue',
      options: ['电影院', '公园', '商场', 'KTV', '展览', '露营', '游乐场', '密室'] },
    { id: 'weekend', name: '周末计划', icon: '📅', color: 'purple',
      options: ['在家躺', '户外游', '逛街', '看展', '运动健身', '学习充电', '约朋友', '周边游'] },
    { id: 'fight', name: '吵架了怎么办', icon: '💔', color: 'red',
      options: ['主动道歉认错', '给彼此冷静空间', '认真沟通讲道理', '哄对方开心', '送个小惊喜', '写信表达心意'] },
    { id: 'anni', name: '纪念日怎么过', icon: '🎊', color: 'orange',
      options: ['出去吃大餐', '在家DIY', '互赠礼物', '短途旅行', '重温初遇地', '给对方惊喜'] },
    { id: 'stale', name: '感情变淡了', icon: '🔥', color: 'yellow',
      options: ['安排一次约会', '深度谈心', '一起做件新鲜事', '制造小惊喜', '回忆美好过去', '计划共同未来'] },
  ],
  custom: [
    { id: 'c1', name: '周末怎么过', icon: '🌤️', color: 'green',
      options: ['宅家休息', '出门浪一天', '约朋友聚', '二人世界', '回家陪家人', '加班搞钱'], isPreset: false },
    { id: 'c2', name: '今晚吃什么', icon: '🍜', color: 'orange',
      options: ['自己做', '点外卖', '出去吃', '随便对付', '一起吃大餐', '减肥不吃了'], isPreset: false },
  ],
};

const ICON_CHOICES = ['🎯','🎲','🎪','🎨','🎭','🎮','🎰','🎵','🎬','📚','🍕','🍜','🍣','🍰','🧁','🍦','☕','🧋','🍺','💐','🌹','🌸','🌟','💎','✨','💫','❤️','💕','🐱','🐶','🦊','🐰','😄','😍','🤗','😅','🎁','🎈','🎉','📅'];
const COLOR_CHOICES = ['pink', 'purple', 'orange', 'blue', 'green', 'yellow', 'red'];
const STICK_COLORS = ['pink', 'purple', 'orange', 'blue', 'green', 'yellow', 'red'];

const RESULT_SUBTEXTS = [
  '天意如此~ 就这么定了！',
  '缘分指引的结果 ✨',
  '看来这就是命定的答案！',
  '不许反悔哦~ 💕',
  '宇宙已经给你答案了',
  '抽签到此，听从天意！',
];

function pad(n) { return n < 10 ? '0' + n : '' + n; }
function timeLabel(ts) {
  const d = new Date(ts);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return '刚刚';
  if (diff < 3600) return Math.floor(diff / 60) + '分钟前';
  if (diff < 86400) return Math.floor(diff / 3600) + '小时前';
  if (diff < 604800) return Math.floor(diff / 86400) + '天前';
  return `${pad(d.getMonth()+1)}.${pad(d.getDate())}`;
}

function generateConfetti() {
  const shapes = ['✦', '✧', '★', '♡', '❤', '✿', '❀', '●', '◆', '▲'];
  const colors = ['#E891A4', '#FFD93D', '#B19CD9', '#FF8E53', '#7BC4E8', '#7BC67B'];
  return Array.from({ length: 30 }, () => ({
    x: Math.random() * 100,
    delay: Math.random() * 2.5,
    shape: shapes[Math.floor(Math.random() * shapes.length)],
    color: colors[Math.floor(Math.random() * colors.length)],
  }));
}

Page({
  data: {
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
    currentView: 'home',         // home | draw | custom
    currentTube: null,           // 当前签筒
    currentSticks: [],           // 抽签台显示的签
    currentResult: null,
    resultEmoji: '',
    resultSubText: '',
    isDrawing: false,
    showResult: false,
    confettiList: [],
    history: [],                 // 抽签历史
    quickTubes: TUBE_TEMPLATES.preset,
    customTubes: TUBE_TEMPLATES.custom,
    editingId: null,             // 编辑中的签筒 id
    customDraft: {
      name: '',
      icon: '🎯',
      color: 'pink',
      options: ['', ''],
    },
    iconChoices: ICON_CHOICES,
    colorChoices: COLOR_CHOICES,
  },

  onLoad() {
    this.refreshHistory();
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' });
    this.refreshHistory();
  },

  refreshHistory() {
    const history = wx.getStorageSync('decision_history') || [];
    history.forEach(h => { h.timeLabel = timeLabel(h.ts); });
    this.setData({ history });
  },

  // ============== 首页操作 ==============
  onPickTube(e) {
    const { id, source } = e.currentTarget.dataset;
    const all = [...TUBE_TEMPLATES.preset, ...TUBE_TEMPLATES.custom];
    const tube = all.find(t => t.id === id);
    if (!tube) return;
    this.startDraw(tube);
  },

  onClearHistory() {
    if (this.data.history.length === 0) return;
    wx.showModal({
      title: '清空记录',
      content: '确定要清空所有抽签历史吗?',
      success: (res) => {
        if (res.confirm) {
          wx.removeStorageSync('decision_history');
          this.setData({ history: [] });
        }
      },
    });
  },

  onRemoveHistory(e) {
    // 点击历史项直接用该签筒重抽
    const { index } = e.currentTarget.dataset;
    const item = this.data.history[index];
    if (!item) return;
    const all = [...TUBE_TEMPLATES.preset, ...TUBE_TEMPLATES.custom];
    const tube = all.find(t => t.id === item.tubeId);
    if (tube) this.startDraw(tube);
  },

  onDeleteTube(e) {
    const { id } = e.currentTarget.dataset;
    wx.showModal({
      title: '删除签筒',
      content: '这个签筒会被删除,确定吗?',
      success: (res) => {
        if (res.confirm) {
          TUBE_TEMPLATES.custom = TUBE_TEMPLATES.custom.filter(t => t.id !== id);
          this.setData({ customTubes: TUBE_TEMPLATES.custom });
        }
      },
    });
  },

  onNewTube() {
    this.setData({
      currentView: 'custom',
      editingId: null,
      customDraft: {
        name: '',
        icon: '🎯',
        color: 'pink',
        options: ['', ''],
      },
    });
  },

  onEditTube() {
    if (!this.data.currentTube) return;
    const tube = this.data.currentTube;
    this.setData({
      currentView: 'custom',
      editingId: tube.id,
      customDraft: {
        name: tube.name,
        icon: tube.icon,
        color: tube.color,
        options: [...tube.options],
      },
    });
  },

  // ============== 抽签台 ==============
  startDraw(tube) {
    const sticks = this.makeSticks(tube.options.length);
    this.setData({
      currentView: 'draw',
      currentTube: tube,
      currentSticks: sticks,
      currentResult: null,
      isDrawing: false,
      showResult: false,
    });
  },

  makeSticks(count) {
    // 控制签的数量在 5-8 之间,超过则取部分
    const display = Math.min(Math.max(count, 5), 8);
    const stickWidth = 22;
    const gap = 26;
    const totalW = (display - 1) * gap;
    const startX = -totalW / 2;
    return Array.from({ length: display }, (_, i) => {
      // 在 -8 ~ 8 度之间随机倾斜
      const rot = (Math.random() - 0.5) * 16;
      // 高度差异让签有错落感
      const heightVar = 250 + Math.random() * 40;
      return {
        id: i,
        x: startX + i * gap,
        rot: rot,
        height: heightVar,
        color: STICK_COLORS[Math.floor(Math.random() * STICK_COLORS.length)],
        shooting: false,
        shownLabel: '',
      };
    });
  },

  onStartDraw() {
    if (this.data.isDrawing) return;
    const tube = this.data.currentTube;
    if (!tube || tube.options.length === 0) return;

    // 重新生成签
    let sticks = this.makeSticks(tube.options.length);
    this.setData({ isDrawing: true, currentResult: null, currentSticks: sticks, showResult: false });

    // 抽签动画时长
    const drawDuration = 1400;
    const shootAt = drawDuration - 300;

    // 阶段1: 摇晃 1.1s
    setTimeout(() => {
      // 阶段2: 选一支签弹出
      const winnerIndex = Math.floor(Math.random() * sticks.length);
      const winner = sticks[winnerIndex];
      const resultIdx = Math.floor(Math.random() * tube.options.length);
      const result = tube.options[resultIdx];

      const shootDirection = winnerIndex % 2 === 0 ? -1 : 1;
      const shootX = shootDirection * (40 + Math.random() * 30);
      const shootY = -(220 + Math.random() * 40);
      const shootRot = shootDirection * (8 + Math.random() * 6);

      sticks = sticks.map((s, i) => i === winnerIndex ? {
        ...s,
        shooting: true,
        shootX: shootX,
        shootY: shootY,
        shootRot: shootRot,
        shownLabel: result,
      } : s);

      this.setData({
        currentSticks: sticks,
        currentResult: result,
      });

      // 阶段3: 弹出 modal
      setTimeout(() => {
        this.setData({
          isDrawing: false,
          showResult: true,
          resultEmoji: tube.icon,
          resultSubText: RESULT_SUBTEXTS[Math.floor(Math.random() * RESULT_SUBTEXTS.length)],
          confettiList: generateConfetti(),
        });
        this.addHistory(tube, result);
      }, 600);
    }, shootAt);
  },

  addHistory(tube, result) {
    const history = wx.getStorageSync('decision_history') || [];
    history.unshift({
      id: Date.now() + '_' + Math.random().toString(36).slice(2, 6),
      tubeId: tube.id,
      tubeName: tube.name,
      option: result,
      ts: Date.now(),
    });
    const trimmed = history.slice(0, 30);
    wx.setStorageSync('decision_history', trimmed);
    this.refreshHistory();
  },

  onCloseResult() {
    this.setData({ showResult: false });
  },

  onStopProp() {
    // 阻止冒泡关闭
  },

  onRedraw() {
    this.setData({ showResult: false, currentResult: null });
    setTimeout(() => this.onStartDraw(), 250);
  },

  onBackToHome() {
    this.setData({
      currentView: 'home',
      currentTube: null,
      currentResult: null,
      showResult: false,
    });
  },

  // ============== 自定义签筒 ==============
  onCustomNameInput(e) {
    this.setData({ 'customDraft.name': e.detail.value });
  },

  onPickColor(e) {
    this.setData({ 'customDraft.color': e.currentTarget.dataset.color });
  },

  onPickIcon(e) {
    this.setData({ 'customDraft.icon': e.currentTarget.dataset.icon });
  },

  onOptionInput(e) {
    const { index } = e.currentTarget.dataset;
    const options = [...this.data.customDraft.options];
    options[index] = e.detail.value;
    this.setData({ 'customDraft.options': options });
  },

  onAddOption() {
    const options = [...this.data.customDraft.options];
    if (options.length >= 20) return;
    options.push('');
    this.setData({ 'customDraft.options': options });
  },

  onRemoveOption(e) {
    const { index } = e.currentTarget.dataset;
    const options = [...this.data.customDraft.options];
    if (options.length <= 2) {
      wx.showToast({ title: '至少保留 2 个选项', icon: 'none' });
      return;
    }
    options.splice(index, 1);
    this.setData({ 'customDraft.options': options });
  },

  onSaveCustom() {
    const draft = this.data.customDraft;
    const name = draft.name.trim();
    const options = draft.options.map(o => o.trim()).filter(o => o.length > 0);

    if (!name) {
      wx.showToast({ title: '请输入签筒名字', icon: 'none' });
      return;
    }
    if (options.length < 2) {
      wx.showToast({ title: '至少需要 2 个选项', icon: 'none' });
      return;
    }
    if (this.data.editingId) {
      // 编辑现有
      TUBE_TEMPLATES.custom = TUBE_TEMPLATES.custom.map(t =>
        t.id === this.data.editingId
          ? { ...t, name, icon: draft.icon, color: draft.color, options }
          : t
      );
    } else {
      // 新建
      const newTube = {
        id: 'c' + Date.now(),
        name,
        icon: draft.icon,
        color: draft.color,
        options,
        isPreset: false,
      };
      TUBE_TEMPLATES.custom.push(newTube);
    }

    this.setData({
      customTubes: TUBE_TEMPLATES.custom,
      currentView: 'home',
      editingId: null,
    });
    wx.showToast({ title: '已保存', icon: 'success' });
  },

  onCancelCustom() {
    this.setData({
      currentView: this.data.editingId ? 'draw' : 'home',
      editingId: null,
    });
  },
});
