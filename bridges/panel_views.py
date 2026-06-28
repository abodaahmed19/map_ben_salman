"""حماية لوحة التحكم بكلمة مرور مشتركة (gate بالجلسة)."""
from django.conf import settings
from django.shortcuts import render, redirect

PANEL_PASSWORD = getattr(settings, "PANEL_PASSWORD", "mbs2026")


def panel_login(request):
    if request.session.get("panel_authed"):
        return redirect("panel")
    error = ""
    if request.method == "POST":
        if request.POST.get("password") == PANEL_PASSWORD:
            request.session["panel_authed"] = True
            return redirect("panel")
        error = "كلمة المرور غير صحيحة"
    return render(request, "panel_login.html", {"error": error})


def panel_view(request):
    if not request.session.get("panel_authed"):
        return redirect("panel_login")
    return render(request, "panel.html")


def panel_logout(request):
    request.session.pop("panel_authed", None)
    return redirect("panel_login")
