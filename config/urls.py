"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from claims import views


urlpatterns = [

    # ========================================================
    # SYSTEM
    # ========================================================

    path(
        'admin/',
        admin.site.urls
    ),

    path(
        '',
        views.home,
        name='home'
    ),

    path(
        'login/',
        views.login_view,
        name='login'
    ),

    path(
        'register/',
        views.register_view,
        name='register'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),


    # ========================================================
    # POLICYHOLDER
    # ========================================================

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),

    path(
        'my-claims/',
        views.my_claims,
        name='my_claims'
    ),

    path(
        'submit-claim/',
        views.submit_claim,
        name='submit_claim'
    ),

    path(
        'claim-details/<str:claim_id>/',
        views.claim_details,
        name='claim_details'
    ),

    path(
        'profile/',
        views.profile,
        name='profile'
    ),

    path(
        'password-change/',
        views.password_change,
        name='password_change'
    ),


    # ========================================================
    # OFFICER
    # ========================================================

    path(
        'officer-dashboard/',
        views.officer_dashboard,
        name='officer_dashboard'
    ),

    path(
        'officer-claims/',
        views.officer_claims,
        name='officer_claims'
    ),

    path(
        'officer-pending/',
        views.officer_pending,
        name='officer_pending'
    ),

    path(
        'officer-reports/',
        views.officer_reports,
        name='officer_reports'
    ),

    path(
        'officer-claim/<str:claim_id>/',
        views.officer_claim_review,
        name='officer_claim_review'
    ),

    path(
        'officer-claim/<str:claim_id>/decision/',
        views.officer_claim_decision,
        name='officer_claim_decision'
    ),


    # ========================================================
    # ADMINISTRATOR
    # ========================================================

    path(
        'admin-dashboard/',
        views.admin_dashboard,
        name='admin_dashboard'
    ),

    path(
    'admin-officers/',
    views.admin_officers,
    name='admin_officers'
),

path(
    'admin-officers/edit/<int:officer_id>/',
    views.admin_edit_officer,
    name='admin_edit_officer'
),

path(
    'admin-officers/toggle/<int:officer_id>/',
    views.admin_toggle_officer,
    name='admin_toggle_officer'
),

path(
    'admin-officers/add/',
    views.admin_add_officer,
    name='admin_add_officer'
),


    path(
        'admin-policyholders/',
        views.admin_policyholders,
        name='admin_policyholders'
    ),

    path(
    'admin-policyholder/<int:user_id>/',
    views.admin_policyholder_details,
    name='admin_policyholder_details'
),

    path(
        'admin-claims/',
        views.admin_claims,
        name='admin_claims'
    ),

    path(
        'admin-claim/<str:claim_id>/',
        views.admin_claim_details,
        name='admin_claim_details'
    ),
    path(
    'admin-claim/<str:claim_id>/assign/',
    views.admin_assign_claim_officer,
    name='admin_assign_claim_officer'
    ),
    path(
    'admin-reports/',
    views.admin_reports,
    name='admin_reports'
    ),
    path(
    'available-policies/',
    views.available_policies,
    name='available_policies'
),

path(
    'register-policy/<int:plan_id>/',
    views.register_policy,
    name='register_policy'
),
path(
    'admin-insurance-plans/',
    views.admin_insurance_plans,
    name='admin_insurance_plans'
),

path(
    'admin-insurance-plans/add/',
    views.admin_add_insurance_plan,
    name='admin_add_insurance_plan'
),

path(
    'admin-insurance-plans/edit/<int:plan_id>/',
    views.admin_edit_insurance_plan,
    name='admin_edit_insurance_plan'
),

path(
    'admin-insurance-plans/toggle/<int:plan_id>/',
    views.admin_toggle_insurance_plan,
    name='admin_toggle_insurance_plan'
),

]


urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)