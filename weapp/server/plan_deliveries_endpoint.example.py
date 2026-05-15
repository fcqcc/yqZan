# -*- coding: utf-8 -*-
"""
存钱计划「存入明细」接口示例 — 接到你现有的 Flask 应用里。

小程序请求：GET /api/plans/<plan_id>/deliveries
需与登录态一致（例如校验 JWT 后，且 plan 属于当前用户/情侣）。

请按你真实的数据库表名、字段名修改 SQL / ORM。
常见表名：plan_delivery、plan_deliveries、savings_records 等。
"""

# ---- 示例：Flask + SQLAlchemy（伪代码，按你项目改写）----
#
# from flask import Blueprint, jsonify, abort
# from flask_jwt_extended import jwt_required, get_jwt_identity
#
# bp = Blueprint("plans", __name__)
#
#
# @bp.get("/api/plans/<int:plan_id>/deliveries")
# @jwt_required()
# def list_plan_deliveries(plan_id):
#     user_id = get_jwt_identity()
#     plan = Plan.query.get(plan_id)
#     if not plan or not user_can_access_plan(user_id, plan):
#         abort(404)
#     rows = (
#         PlanDelivery.query.filter_by(plan_id=plan_id)
#         .order_by(PlanDelivery.created_at.desc())
#         .all()
#     )
#     return jsonify(
#         [
#             {
#                 "id": r.id,
#                 "amount": float(r.amount),
#                 "note": r.note or "",
#                 "created_at": r.created_at.isoformat() if r.created_at else "",
#             }
#             for r in rows
#         ]
#     )


# ---- 或：在 GET /api/plans 列表里直接带上 deliveries，小程序会识别并不再单独请求 ----
#
# return jsonify(
#     [
#         {
#             "id": p.id,
#             "title": p.title,
#             "target_amount": p.target_amount,
#             "current_amount": p.current_amount,
#             "done": p.done,
#             "deadline_date": p.deadline_date,
#             "deliveries": [
#                 {
#                     "id": d.id,
#                     "amount": float(d.amount),
#                     "note": d.note or "",
#                     "created_at": d.created_at.isoformat(),
#                 }
#                 for d in p.deliveries
#             ],
#         }
#         for p in plans
#     ]
# )
