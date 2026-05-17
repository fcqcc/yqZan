/**
 * 小程序端功能开关（可按需修改）
 *
 * FETCH_PLAN_DELIVERIES：
 * - 为 false 时，展开计划不会请求 GET /api/plans/:id/deliveries，避免后端未实现时的 404。
 * - 后端实现该接口后改为 true；或在 GET /api/plans 的每个计划里直接返回 deliveries 数组（有则同样不再请求）。
 */
module.exports = {
  FETCH_PLAN_DELIVERIES: false
}
