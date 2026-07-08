from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from bridges.panel_views import panel_login, panel_view, panel_logout

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("bridges.urls")),
    path("", TemplateView.as_view(template_name="index.html"), name="viewer"),
    path("projects/", TemplateView.as_view(template_name="projects.html", extra_context={"page_category": "current"}), name="projects"),
    path("projects-2028/", TemplateView.as_view(template_name="projects.html", extra_context={"page_category": "new2028"}), name="projects_2028"),
    path("panel/login/", panel_login, name="panel_login"),
    path("panel/logout/", panel_logout, name="panel_logout"),
    path("panel/", panel_view, name="panel"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
