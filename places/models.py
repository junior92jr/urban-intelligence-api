from typing import override

from django.db import models


class PlaceCategory(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    osm_key = models.CharField(max_length=50)
    osm_value = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    include_in_default_search = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=("osm_key", "osm_value"),
                name="unique_place_category_osm_tag",
            ),
        ]
        verbose_name = "place category"
        verbose_name_plural = "place categories"

    @override
    def __str__(self) -> str:
        return str(self.name)
