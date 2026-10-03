from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ============================================================
# USER PROFILE
# ============================================================

class UserProfile(models.Model):

    ROLE_CHOICES = [
        ('policyholder', 'Policyholder'),
        ('officer', 'Claim Officer'),
        ('admin', 'Administrator'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='policyholder'
    )

    phone_number = models.CharField(
    max_length=10,
    unique=True,
    blank=True,
    null=True
)

    driving_license_number = models.CharField(
    max_length=20,
    unique=True,
    blank=True,
    null=True
)

    address = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.username


# ============================================================
# INSURANCE PLAN
# ============================================================

class InsurancePlan(models.Model):

    PLAN_TYPE_CHOICES = [
        ('Comprehensive', 'Comprehensive'),
        ('Third Party', 'Third Party'),
        ('Own Damage', 'Own Damage'),
    ]

    name = models.CharField(
        max_length=100
    )

    plan_type = models.CharField(
        max_length=50,
        choices=PLAN_TYPE_CHOICES
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    insured_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    premium = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    duration_years = models.PositiveIntegerField(
        default=1
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        default=timezone.now
    )

    def __str__(self):
        return self.name


# ============================================================
# REGISTERED POLICY
# ============================================================

class Policy(models.Model):

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
    ]

    FUEL_TYPE_CHOICES = [
        ('Petrol', 'Petrol'),
        ('Diesel', 'Diesel'),
        ('CNG', 'CNG'),
        ('Electric', 'Electric'),
        ('Hybrid', 'Hybrid'),
        ('Other', 'Other'),
    ]

    NOMINEE_RELATION_CHOICES = [
        ('Father', 'Father'),
        ('Mother', 'Mother'),
        ('Spouse', 'Spouse'),
        ('Son', 'Son'),
        ('Daughter', 'Daughter'),
        ('Brother', 'Brother'),
        ('Sister', 'Sister'),
        ('Other', 'Other'),
    ]

    policyholder = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='policies'
    )

    insurance_plan = models.ForeignKey(
    InsurancePlan,
    on_delete=models.PROTECT,
    related_name='policies',
    null=True,
    blank=True
)

    # --------------------------------------------------------
    # Policy Number
    # --------------------------------------------------------

    policy_number = models.CharField(
        max_length=50,
        unique=True
    )

    # --------------------------------------------------------
    # Policyholder Details
    # --------------------------------------------------------

    full_name = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    address = models.TextField(null=True,blank=True)

    # --------------------------------------------------------
    # Vehicle Details
    # --------------------------------------------------------

    vehicle_make = models.CharField(
        max_length=50
    )

    vehicle_model = models.CharField(
        max_length=50
    )

    vehicle_variant = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    vehicle_year = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    registration_number = models.CharField(
        max_length=30
    )

    fuel_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        blank=True,
        null=True
    )

    # --------------------------------------------------------
    # Policy Details
    # --------------------------------------------------------

    coverage_type = models.CharField(
        max_length=100
    )

    insured_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    start_date = models.DateField()

    end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # --------------------------------------------------------
    # Previous Insurance
    # --------------------------------------------------------

    previous_insurer = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    previous_policy_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    previous_policy_expiry = models.DateField(
        blank=True,
        null=True
    )

    no_claim_bonus = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # --------------------------------------------------------
    # Nominee Details
    # --------------------------------------------------------

    nominee_name = models.CharField(
        max_length=150,
        null=True,
        blank=True
    )

    nominee_relationship = models.CharField(
        max_length=50,
        choices=NOMINEE_RELATION_CHOICES,
        null=True,
        blank=True
    )

    nominee_date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    # --------------------------------------------------------
    # Declaration
    # --------------------------------------------------------

    declaration_accepted = models.BooleanField(
        default=False
    )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    created_at = models.DateTimeField(
        default=timezone.now
    )

    def __str__(self):
        return (
            f"{self.policy_number} - "
            f"{self.vehicle_make} {self.vehicle_model}"
        )


# ============================================================
# CLAIM
# ============================================================

class Claim(models.Model):

    STATUS_CHOICES = [
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('investigation', 'Investigation Required'),
    ]

    RISK_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    claim_id = models.CharField(
        max_length=20,
        unique=True
    )

    policyholder = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    # --------------------------------------------------------
    # Registered Policy
    # --------------------------------------------------------

    policy = models.ForeignKey(
        Policy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='claims'
    )

    # --------------------------------------------------------
    # Policy Details
    # --------------------------------------------------------

    policy_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    policy_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # --------------------------------------------------------
    # Vehicle Details
    # --------------------------------------------------------

    vehicle_make = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    vehicle_model = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    vehicle_year = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    registration_number = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

        # --------------------------------------------------------
    # Accident / Incident Details
    # --------------------------------------------------------

    incident_date = models.DateField()

    incident_time = models.TimeField(
        blank=True,
        null=True
    )

    accident_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    accident_location = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    description = models.TextField()

    # --------------------------------------------------------
    # Police / FIR Details
    # --------------------------------------------------------

    POLICE_REPORT_STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('not_reported', 'Not Reported'),
        ('not_required', 'Not Required'),
    ]

    police_report_status = models.CharField(
        max_length=20,
        choices=POLICE_REPORT_STATUS_CHOICES,
        default='not_required'
    )

    police_report_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    police_station = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    police_report_date = models.DateField(
        blank=True,
        null=True
    )

    # --------------------------------------------------------
    # Driver Details
    # --------------------------------------------------------

    driver_name = models.CharField(
    max_length=150,
    blank=True,
    null=True
)

    driving_license_number = models.CharField(
    max_length=30,
    blank=True,
    null=True
)
    
    driver_age = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    driver_authorised = models.BooleanField(
        null=True,
        blank=True
    )

    # --------------------------------------------------------
    # Third-Party / Other Vehicle Details
    # --------------------------------------------------------

    third_party_involved = models.BooleanField(
        default=False
    )

    third_party_injury = models.BooleanField(
        default=False
    )

    third_party_damage = models.BooleanField(
        default=False
    )

    # --------------------------------------------------------
    # Claim Details
    # --------------------------------------------------------

    estimated_damage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    claim_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    damage_description = models.TextField(
        blank=True,
        null=True
    )

    damaged_parts = models.TextField(
    blank=True,
    null=True
)

    police_not_reported_reason = models.TextField(
    blank=True,
    null=True
)

    previous_claims = models.PositiveIntegerField(
    default=0
)

    days_to_report = models.PositiveIntegerField(
    default=0
)

    # --------------------------------------------------------
    # Risk and Status
    # --------------------------------------------------------

    risk_level = models.CharField(
        max_length=20,
        choices=RISK_CHOICES,
        default='low'
    )

    ai_confidence = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    null=True,
    blank=True
)

    low_probability = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    null=True,
    blank=True
)

    medium_probability = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    null=True,
    blank=True
)

    high_probability = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    null=True,
    blank=True
)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='under_review'
    )

    created_at = models.DateTimeField(
    default=timezone.now
    )

    officer_decision = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    officer_remarks = models.TextField(
        blank=True,
        null=True
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claims'
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    assigned_officer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_claims'
    )

    def __str__(self):
        return self.claim_id


# ============================================================
# CLAIM DOCUMENT
# ============================================================

class ClaimDocument(models.Model):

    DOCUMENT_TYPES = [
        ('driving_license', 'Driving License'),
        ('vehicle_registration', 'Vehicle Registration Certificate'),
        ('insurance_policy', 'Insurance Policy'),
        ('repair_estimate', 'Repair Estimate'),
        ('police_report', 'Police Report'),
    ]

    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPES
    )

    file = models.FileField(
        upload_to='claim_documents/'
    )

    extracted_text = models.TextField(
    blank=True,
    null=True
)

    ai_summary = models.TextField(
    blank=True,
    null=True
)

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return f"{self.claim.claim_id} - {self.document_type}"