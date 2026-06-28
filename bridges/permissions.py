from rest_framework.permissions import BasePermission, SAFE_METHODS


class ReadOnlyOrPanelAuthed(BasePermission):
    """القراءة متاحة للجميع (صفحة العرض)، والتعديل يتطلب تسجيل دخول لوحة التحكم."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.session.get("panel_authed"))
