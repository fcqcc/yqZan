// pages/calendar/calendar.js — 存钱日历
const STORAGE_KEYS = {
  anniversaries: 'cal_anniversaries',
  savings: 'cal_savings',
};

const ANNIV_PRESET = [
  { id: 'a1', name: '恋爱纪念日', icon: '💕', color: '#E891A4', date: '2023-06-18', recurring: true },
  { id: 'a2', name: '小可爱生日', icon: '🎂', color: '#FF8E53', date: '1995-08-20', recurring: true, isBirthday: true },
  { id: 'a3', name: '小帅比生日', icon: '🎁', color: '#B19CD9', date: '1994-12-03', recurring: true, isBirthday: true },
  { id: 'a4', name: '第一次接吻', icon: '💋', color: '#FF6B6B', date: '2023-07-22', recurring: true },
  { id: 'a5', name: '一起去旅行', icon: '✈️', color: '#7BC4E8', date: '2024-01-01', recurring: true },
];

const SAVINGS_PRESET = [
  { id: 's1', date: todayStr(-3), amount: 50,  planId: 'p1', planName: '蜜月旅行', planIcon: '🏝️', note: '工资到账，存起来~' },
  { id: 's2', date: todayStr(-3), amount: 20,  planId: 'p1', planName: '蜜月旅行', planIcon: '🏝️', note: '零钱攒的' },
  { id: 's3', date: todayStr(-1), amount: 100, planId: 'p2', planName: '购房首付', planIcon: '🏠', note: 'bonus 拿了一笔' },
  { id: 's4', date: todayStr(-7), amount: 200, planId: 'p1', planName: '蜜月旅行', planIcon: '🏝️', note: '' },
  { id: 's5', date: todayStr(-10), amount: 30, planId: 'p3', planName: '日常基金', planIcon: '☕', note: '奶茶钱省下来' },
  { id: 's6', date: todayStr(-14), amount: 500, planId: 'p2', planName: '购房首付', planIcon: '🏠', note: '年终奖' },
  { id: 's7', date: todayStr(0), amount: 88, planId: 'p1', planName: '蜜月旅行', planIcon: '🏝️', note: '今天也加油!' },
];

const PLANS = [
  { id: 'p1', name: '蜜月旅行', icon: '🏝️' },
  { id: 'p2', name: '购房首付', icon: '🏠' },
  { id: 'p3', name: '日常基金', icon: '☕' },
  { id: 'p4', name: '生日礼物', icon: '🎁' },
];

const WEEKDAYS = [
  { label: '日', isWeekend: true },
  { label: '一', isWeekend: false },
  { label: '二', isWeekend: false },
  { label: '三', isWeekend: false },
  { label: '四', isWeekend: false },
  { label: '五', isWeekend: false },
  { label: '六', isWeekend: true },
];
const WEEKDAY_LABELS_FULL = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
const QUICK_AMOUNTS = [10, 20, 50, 100, 200, 500];

function pad(n) { return n < 10 ? '0' + n : '' + n; }
function todayStr(offset = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
function dateStr(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function daysBetween(d1, d2) {
  return Math.round((d2 - d1) / 86400000);
}

Page({
  data: {
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
    weekdays: WEEKDAYS,
    currentYear: 0,
    currentMonth: 0,           // 1-12
    currentMonthText: '',
    weekdayFirstText: '',
    isCurrentMonth: true,
    calendarDays: [],
    selectedDate: '',
    selectedDay: 0,
    selectedWeekday: '',
    selectedDateLabel: '',
    selectedRelative: '',
    selectedIsToday: false,
    selectedAnnivs: [],
    selectedSavings: [],
    selectedTotal: '0',
    monthTotal: '0',
    monthSavingsCount: 0,
    monthAnnivCount: 0,
    // 弹层
    showAdd: false,
    addDateLabel: '',
    addDraft: { amount: '', planId: '', note: '' },
    plans: PLANS,
    quickAmounts: QUICK_AMOUNTS,
    // 内部数据
    _anniversaries: [],
    _savings: [],
  },

  onLoad() {
    this.loadData();
    const today = new Date();
    this.setCurrentMonth(today.getFullYear(), today.getMonth() + 1);
    this.setData({ selectedDate: dateStr(today) });
    this.refreshSelected();
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' });
    this.loadData();
    this.refreshCalendar();
    this.refreshSelected();
  },

  loadData() {
    let annivs = wx.getStorageSync(STORAGE_KEYS.anniversaries);
    if (!annivs) {
      annivs = ANNIV_PRESET;
      wx.setStorageSync(STORAGE_KEYS.anniversaries, annivs);
    }
    let savings = wx.getStorageSync(STORAGE_KEYS.savings);
    if (!savings) {
      savings = SAVINGS_PRESET;
      wx.setStorageSync(STORAGE_KEYS.savings, savings);
    }
    this.setData({ _anniversaries: annivs, _savings: savings });
  },

  setCurrentMonth(year, month) {
    const today = new Date();
    const isCurrent = (year === today.getFullYear() && month === today.getMonth() + 1);
    const firstDay = new Date(year, month - 1, 1);
    const weekdayFirst = WEEKDAY_LABELS_FULL[firstDay.getDay()];

    this.setData({
      currentYear: year,
      currentMonth: month,
      currentMonthText: month + '月',
      weekdayFirstText: weekdayFirst + '开始',
      isCurrentMonth: isCurrent,
    });
    this.refreshCalendar();
    this.refreshMonthStats();
  },

  refreshCalendar() {
    const { currentYear: y, currentMonth: m } = this.data;
    const todayStrNow = dateStr(new Date());

    const firstDay = new Date(y, m - 1, 1);
    const firstDayOfWeek = firstDay.getDay();
    const daysInMonth = new Date(y, m, 0).getDate();
    const daysInPrevMonth = new Date(y, m - 1, 0).getDate();

    const cells = [];

    // 上月补位
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      const d = daysInPrevMonth - i;
      const prevM = m - 1;
      const prevY = prevM === 0 ? y - 1 : y;
      const prevMM = prevM === 0 ? 12 : prevM;
      const date = `${prevY}-${pad(prevMM)}-${pad(d)}`;
      const cellData = this.buildCellData(date, d, false, todayStrNow);
      cells.push(cellData);
    }

    // 当月
    for (let d = 1; d <= daysInMonth; d++) {
      const date = `${y}-${pad(m)}-${pad(d)}`;
      const cellData = this.buildCellData(date, d, true, todayStrNow);
      cells.push(cellData);
    }

    // 下月补位（凑齐 42 个）
    const remaining = 42 - cells.length;
    for (let d = 1; d <= remaining; d++) {
      const nextM = m + 1;
      const nextY = nextM === 13 ? y + 1 : y;
      const nextMM = nextM === 13 ? 1 : nextM;
      const date = `${nextY}-${pad(nextMM)}-${pad(d)}`;
      const cellData = this.buildCellData(date, d, false, todayStrNow);
      cells.push(cellData);
    }

    this.setData({ calendarDays: cells });
  },

  buildCellData(date, day, isCurrentMonth, todayStrNow) {
    const isToday = date === todayStrNow;
    const future = date > todayStrNow;
    const annivs = this.findAnniversariesForDate(date);
    const savingsForDate = this.data._savings.filter(s => s.date === date);
    const hasSavings = savingsForDate.length > 0;
    const savingsTotal = savingsForDate.reduce((sum, s) => sum + Number(s.amount || 0), 0);

    const firstAnniv = annivs[0] || null;

    return {
      date,
      day,
      isCurrentMonth,
      isToday,
      isFuture: future,
      hasAnniv: annivs.length > 0,
      firstAnnivIcon: firstAnniv ? firstAnniv.icon : '',
      firstAnnivColor: firstAnniv ? firstAnniv.color : '',
      hasSavings,
      savingsTotal: hasSavings ? savingsTotal : 0,
    };
  },

  findAnniversariesForDate(date) {
    const [y, m, d] = date.split('-').map(Number);
    const matched = [];
    this.data._anniversaries.forEach(a => {
      const [ay, am, ad] = a.date.split('-').map(Number);
      if (a.recurring) {
        if (am === m && ad === d) {
          matched.push(this.enrichAnniv(a, date));
        }
      } else {
        if (a.date === date) {
          matched.push(this.enrichAnniv(a, date));
        }
      }
    });
    return matched;
  },

  enrichAnniv(anniv, date) {
    const today = new Date();
    const target = new Date(date);
    const diff = daysBetween(today, target);
    let daysNum, daysUnit, daysColor, metaText;

    if (diff === 0) {
      daysNum = '今';
      daysUnit = '天!';
      daysColor = '#E891A4';
      metaText = '就是今天 🎉';
    } else if (diff > 0) {
      daysNum = String(diff);
      daysUnit = '天后';
      daysColor = '#5BA85B';
      metaText = anniv.recurring ? '每年这天' : '一次纪念';
    } else {
      daysNum = String(-diff);
      daysUnit = '天前';
      daysColor = '#8B7A8E';
      metaText = anniv.recurring ? '每年这天' : '一次纪念';
    }

    return { ...anniv, daysNum, daysUnit, daysColor, metaText };
  },

  refreshSelected() {
    const { selectedDate } = this.data;
    if (!selectedDate) return;
    const [y, m, d] = selectedDate.split('-').map(Number);
    const date = new Date(y, m - 1, d);
    const today = new Date();
    const isToday = dateStr(date) === dateStr(today);
    const diff = daysBetween(today, date);
    let relative = '';
    if (diff === 0) relative = '今天';
    else if (diff === 1) relative = '明天';
    else if (diff === -1) relative = '昨天';
    else if (diff > 0) relative = diff + ' 天后';
    else relative = (-diff) + ' 天前';

    const annivs = this.findAnniversariesForDate(selectedDate);
    const savings = this.data._savings
      .filter(s => s.date === selectedDate)
      .sort((a, b) => (b.id || 0) - (a.id || 0));
    const total = savings.reduce((sum, s) => sum + Number(s.amount || 0), 0);

    this.setData({
      selectedDay: d,
      selectedWeekday: WEEKDAY_LABELS_FULL[date.getDay()],
      selectedDateLabel: `${y}年${m}月${d}日`,
      selectedRelative: relative,
      selectedIsToday: isToday,
      selectedAnnivs: annivs,
      selectedSavings: savings,
      selectedTotal: total.toLocaleString('zh-CN'),
    });
  },

  refreshMonthStats() {
    const { currentYear: y, currentMonth: m } = this.data;
    const monthPrefix = `${y}-${pad(m)}`;
    const monthSavings = this.data._savings.filter(s => s.date.startsWith(monthPrefix));
    const total = monthSavings.reduce((sum, s) => sum + Number(s.amount || 0), 0);

    // 该月纪念日数（去重按月日）
    const annivSet = new Set();
    this.data._anniversaries.forEach(a => {
      const [, am, ad] = a.date.split('-').map(Number);
      if (a.recurring) annivSet.add(`${pad(am)}-${pad(ad)}`);
      else if (a.date.startsWith(monthPrefix)) annivSet.add(a.date);
    });

    // 不同存钱日
    const daySet = new Set(monthSavings.map(s => s.date));

    this.setData({
      monthTotal: total.toLocaleString('zh-CN'),
      monthSavingsCount: daySet.size,
      monthAnnivCount: annivSet.size,
    });
  },

  // ============== 月份切换 ==============
  onPrevMonth() {
    let { currentYear: y, currentMonth: m } = this.data;
    m--;
    if (m < 1) { m = 12; y--; }
    this.setCurrentMonth(y, m);
  },

  onNextMonth() {
    let { currentYear: y, currentMonth: m } = this.data;
    m++;
    if (m > 12) { m = 1; y++; }
    this.setCurrentMonth(y, m);
  },

  onPickMonth() {
    // 简单处理：直接跳回今天
    const today = new Date();
    this.setCurrentMonth(today.getFullYear(), today.getMonth() + 1);
  },

  onGoToday() {
    const today = new Date();
    this.setCurrentMonth(today.getFullYear(), today.getMonth() + 1);
    this.setData({ selectedDate: dateStr(today) });
    this.refreshSelected();
  },

  // ============== 选择日期 ==============
  onSelectDate(e) {
    const { date } = e.currentTarget.dataset;
    // 跨月点击时切换月份
    const [y, m] = date.split('-').map(Number);
    if (y !== this.data.currentYear || m !== this.data.currentMonth) {
      this.setCurrentMonth(y, m);
    }
    this.setData({ selectedDate: date });
    this.refreshSelected();
  },

  onTapAnniv(e) {
    const { id } = e.currentTarget.dataset;
    const anniv = this.data.selectedAnnivs.find(a => a.id === id);
    if (!anniv) return;
    wx.showModal({
      title: anniv.name,
      content: `${anniv.date}\n${anniv.recurring ? '每年纪念' : '一次性纪念'}\n${anniv.metaText}`,
      confirmText: '知道了',
      showCancel: false,
    });
  },

  // ============== 记一笔 ==============
  onOpenAdd() {
    this.setData({
      showAdd: true,
      addDateLabel: this.data.selectedDateLabel,
      addDraft: { amount: '', planId: '', note: '' },
    });
  },

  onCloseAdd() {
    this.setData({ showAdd: false });
  },

  onStopProp() {},

  onAmountInput(e) {
    const v = e.detail.value;
    // 只能数字 + 小数点
    const clean = v.replace(/[^\d.]/g, '');
    this.setData({ 'addDraft.amount': clean });
  },

  onPickQuickAmount(e) {
    const { amount } = e.currentTarget.dataset;
    this.setData({ 'addDraft.amount': String(amount) });
  },

  onPickPlan(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({ 'addDraft.planId': id });
  },

  onNoteInput(e) {
    this.setData({ 'addDraft.note': e.detail.value });
  },

  onSaveRecord() {
    const { amount, planId, note } = this.data.addDraft;
    const amt = Number(amount);
    if (!amt || amt <= 0) {
      wx.showToast({ title: '请输入金额', icon: 'none' });
      return;
    }
    const plan = this.data.plans.find(p => p.id === planId);
    const record = {
      id: 's' + Date.now() + '_' + Math.random().toString(36).slice(2, 6),
      date: this.data.selectedDate,
      amount: amt,
      planId: plan ? plan.id : '',
      planName: plan ? plan.name : '',
      planIcon: plan ? plan.icon : '💰',
      note: note || '',
    };
    const savings = [record, ...this.data._savings];
    wx.setStorageSync(STORAGE_KEYS.savings, savings);
    this.setData({ _savings: savings, showAdd: false });
    this.refreshCalendar();
    this.refreshSelected();
    this.refreshMonthStats();
    wx.showToast({ title: '✨ 记录成功', icon: 'success' });
  },

  // ============== 纪念日（占位实现） ==============
  onAddAnniv() {
    wx.showModal({
      title: '添加纪念日',
      content: '纪念日管理模块：可设置每年循环（如生日）或单次纪念（如婚礼）。\n完整功能：调用 wx.navigateTo 跳转独立的纪念日管理页。',
      showCancel: false,
      confirmText: '好的',
    });
  },
});
