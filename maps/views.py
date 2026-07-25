from typing import Any, override

from django.conf import settings
from django.views.generic import TemplateView


class MapView(TemplateView):
    template_name = "maps/index.html"

    @override
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["map_tile_url"] = settings.MAP_TILE_URL
        context["map_tile_attribution"] = settings.MAP_TILE_ATTRIBUTION

        return context
