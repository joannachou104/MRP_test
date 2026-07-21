"""簡易權限模擬(本機測試用,非正式帳密系統)。

前端透過 Header 傳送目前選定的操作角色與姓名:
  X-User-Name: 顯示用姓名(percent-encoded,因 HTTP header 值需為 ISO-8859-1)
  X-User-Role: admin | procurement | viewer

需商品管理或採購人員權限的操作(登記在途/確認到貨/標記忽略)
僅允許 admin / procurement 角色執行。
"""
from urllib.parse import unquote
from fastapi import Header, HTTPException


PERMITTED_ROLES_FOR_PROCUREMENT_ACTIONS = {"admin", "procurement"}


class CurrentUser:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role


def get_current_user(
    x_user_name: str = Header(default="測試使用者"),
    x_user_role: str = Header(default="admin"),
) -> CurrentUser:
    try:
        name = unquote(x_user_name)
    except Exception:  # noqa: BLE001
        name = x_user_name
    return CurrentUser(name=name, role=x_user_role)


def require_procurement_permission(user: CurrentUser) -> None:
    if user.role not in PERMITTED_ROLES_FOR_PROCUREMENT_ACTIONS:
        raise HTTPException(
            status_code=403,
            detail="此操作需具備商品管理或採購人員權限(admin / procurement)",
        )
