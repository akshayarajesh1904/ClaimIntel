from django.contrib import admin

from .models import (
    UserProfile,
    Policy,
    Claim,
    ClaimDocument
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'role',
    )


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):

    list_display = (
        'policy_number',
        'policyholder',
        'vehicle_make',
        'vehicle_model',
        'registration_number',
        'coverage_type',
        'start_date',
        'end_date',
        'status',
    )

    search_fields = (
        'policy_number',
        'policyholder__email',
        'registration_number',
    )


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):

    list_display = (
        'claim_id',
        'policyholder',
        'policy',
        'assigned_officer',
        'reviewed_by',
        'status',
        'risk_level',
        'created_at',
    )

    search_fields = (
        'claim_id',
        'policy_number',
        'policyholder__email',
    )


@admin.register(ClaimDocument)
class ClaimDocumentAdmin(admin.ModelAdmin):

    list_display = (
        'claim',
        'document_type',
        'uploaded_at',
    )