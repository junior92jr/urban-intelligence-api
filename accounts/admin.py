from typing import TYPE_CHECKING

from django.contrib import admin

from accounts.models import AccountToken, User, UserProfile

if TYPE_CHECKING:
    _UserModelAdmin = admin.ModelAdmin[User]
    _UserProfileModelAdmin = admin.ModelAdmin[UserProfile]
    _AccountTokenModelAdmin = admin.ModelAdmin[AccountToken]
else:
    _UserModelAdmin = admin.ModelAdmin
    _UserProfileModelAdmin = admin.ModelAdmin
    _AccountTokenModelAdmin = admin.ModelAdmin


@admin.register(User)
class UserAdmin(_UserModelAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)


@admin.register(UserProfile)
class UserProfileAdmin(_UserProfileModelAdmin):
    list_display = (
        "user",
        "service_area",
        "location_sharing_enabled",
        "preferred_radius",
        "onboarding_completed_at",
    )
    autocomplete_fields = ("service_area",)
    list_filter = ("location_sharing_enabled", "service_area__country", "service_area")
    search_fields = ("user__email", "service_area__name", "service_area__country__name")


@admin.register(AccountToken)
class AccountTokenAdmin(_AccountTokenModelAdmin):
    list_display = ("user", "purpose", "created_at", "expires_at", "used_at")
    list_filter = ("purpose", "used_at")
    search_fields = ("user__email", "token_hash")
