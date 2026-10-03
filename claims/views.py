from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.db.models import Count, Q
import re
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from .models import UserProfile, Policy, Claim, ClaimDocument, InsurancePlan
from django.db import models
from datetime import date
from dateutil.relativedelta import relativedelta
from claims.ml.predict import predict_claim_risk, generate_claim_explanation
from .document_ai import process_document
from dateutil.relativedelta import relativedelta
import json
# ============================================================
# HOME
# ============================================================

def home(request):
    return render(request, 'index.html')



# ============================================================
# REGISTER
# ============================================================

def register_view(request):

    if request.method == 'POST':

        validate_field = request.POST.get('validate_field', '').strip()

        if validate_field:
            value = request.POST.get('value', '').strip()

            if validate_field == 'email':
                value = value.lower()
                try:
                    validate_email(value)
                except ValidationError:
                    return JsonResponse({'valid': False, 'message': 'Please enter a valid email address.'})

                if not re.fullmatch(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',value):
                    return JsonResponse({
        'valid': False,
        'message': 'Please enter a valid email address.'
    })

                if User.objects.filter(email__iexact=value).exists():
                    return JsonResponse({'valid': False, 'message': 'An account with this email already exists.'})

                return JsonResponse({'valid': True, 'message': 'Email is available.'})

            if validate_field == 'phone_number':
                if not re.fullmatch(r'[6-9][0-9]{9}', value):
                    return JsonResponse({'valid': False, 'message': 'Phone number must be 10 digits and start with 6-9.'})

                if re.fullmatch(r'(\d)\1{9}', value):
                    return JsonResponse({'valid': False, 'message': 'Please enter a valid phone number.'})

                if UserProfile.objects.filter(phone_number=value).exists():
                    return JsonResponse({'valid': False, 'message': 'This phone number is already registered.'})

                return JsonResponse({'valid': True, 'message': 'Phone number is available.'})

            if validate_field == 'driver_license_number':
                value = value.upper()
                license_pattern = r'^[A-Z]{2}[0-9]{2}[0-9]{4,11}$'

                if not re.fullmatch(license_pattern, value):
                    return JsonResponse({'valid': False, 'message': 'Please enter a valid Indian driving license number.'})

                if UserProfile.objects.filter(driving_license_number__iexact=value).exists():
                    return JsonResponse({'valid': False, 'message': 'This driving license number is already registered.'})

                return JsonResponse({'valid': True, 'message': 'Driving license number is available.'})

            return JsonResponse({'valid': False, 'message': 'Invalid validation request.'})

        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone_number = request.POST.get('phone_number', '').strip()
        driver_license_number = request.POST.get('driver_license_number', '').strip().upper()
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        try:
            validate_email(email)
        except ValidationError:
            return render(request, 'register.html', {'error': 'Please enter a valid email address.'})

        if not re.fullmatch(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',email):
            return render(request, 'register.html', {'error': 'Please enter a valid email address.'})

        if not re.fullmatch(r'[6-9][0-9]{9}', phone_number):
            return render(request, 'register.html', {'error': 'Please enter a valid 10-digit Indian mobile number.'})

        if re.fullmatch(r'(\d)\1{9}', phone_number):
            return render(request, 'register.html', {'error': 'Please enter a valid mobile number.'})

        license_pattern = r'^[A-Z]{2}[0-9]{2}[0-9]{4,11}$'
        if not re.fullmatch(license_pattern, driver_license_number):
            return render(request, 'register.html', {'error': 'Please enter a valid Indian driving license number.'})

        if User.objects.filter(email__iexact=email).exists():
            return render(request, 'register.html', {'error': 'An account with this email already exists.'})

        if UserProfile.objects.filter(phone_number=phone_number).exists():
            return render(request, 'register.html', {'error': 'This phone number is already registered.'})

        if UserProfile.objects.filter(driving_license_number__iexact=driver_license_number).exists():
            return render(request, 'register.html', {'error': 'This driving license number is already registered.'})

        if password != confirm_password:
            return render(request, 'register.html', {'error': 'Passwords do not match.'})

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        UserProfile.objects.create(
            user=user,
            role='policyholder',
            phone_number=phone_number,
            driving_license_number=driver_license_number,
            address=address
        )

        login(request, user)

        return redirect('/dashboard/')

    return render(request, 'register.html')


# ============================================================
# LOGIN
# ============================================================

def login_view(request):

    if request.method == 'POST':

        email = request.POST.get(
            'username',
            ''
        ).strip().lower()

        password = request.POST.get(
            'password',
            ''
        )

        # ----------------------------------------------------
        # Find user using email
        # ----------------------------------------------------

        try:

            user = User.objects.get(
                email__iexact=email
            )

        except User.DoesNotExist:

            return render(
                request,
                'index.html',
                {
                    'error':
                        'Username or password is incorrect.'
                }
            )

        # ----------------------------------------------------
        # Authenticate using Django username
        # ----------------------------------------------------

        authenticated_user = authenticate(
            request,
            username=user.username,
            password=password
        )

        if authenticated_user is not None:

            login(
                request,
                authenticated_user
            )

            # ------------------------------------------------
            # Redirect according to role
            # ------------------------------------------------

            try:

                profile = UserProfile.objects.get(
                    user=authenticated_user
                )

                if profile.role == 'admin':

                    return redirect(
                        '/admin-dashboard/'
                    )

                elif profile.role == 'officer':

                    return redirect(
                        '/officer-dashboard/'
                    )

                else:

                    return redirect(
                        '/dashboard/'
                    )

            except UserProfile.DoesNotExist:

                return redirect(
                    '/dashboard/'
                )

        # ----------------------------------------------------
        # Wrong password
        # ----------------------------------------------------

        return render(
            request,
            'index.html',
            {
                'error':
                    'Username or password is incorrect.'
            }
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        'index.html'
    )


# ============================================================
# LOGOUT
# ============================================================

def logout_view(request):

    logout(request)

    return redirect('/')


# ============================================================
# POLICYHOLDER DASHBOARD
# ============================================================

def dashboard(request):

    if not request.user.is_authenticated:
        return redirect('/')

    # --------------------------------------------------------
    # Get claims belonging only to the logged-in policyholder
    # --------------------------------------------------------

    claims = Claim.objects.filter(
        policyholder=request.user
    ).order_by(
        '-created_at'
    )

    # --------------------------------------------------------
    # Claim statistics
    # --------------------------------------------------------

    total_claims = claims.count()

    pending_claims = claims.filter(
        status='under_review'
    ).count()

    approved_claims = claims.filter(
        status='approved'
    ).count()

    # --------------------------------------------------------
    # Recent claims
    # --------------------------------------------------------

    recent_claims = claims[:5]

    # --------------------------------------------------------
    # Render dashboard
    # --------------------------------------------------------

    return render(
        request,
        'dashboard.html',
        {
            'user': request.user,

            'total_claims': total_claims,
            'pending_claims': pending_claims,
            'approved_claims': approved_claims,

            'recent_claims': recent_claims,
        }
    )


# ============================================================
# MY CLAIMS
# ============================================================

def my_claims(request):

    if not request.user.is_authenticated:
        return redirect('/')
    print(
    "LOGGED IN USER:",
    request.user.id,
    request.user.username,
    request.user.email
)

# Get only policies that do NOT already have a claim
    claimed_policy_ids = Claim.objects.filter(
    policyholder=request.user
).values_list(
    'policy_id',
    flat=True
)
    policies = Policy.objects.filter(
    policyholder=request.user
).exclude(
    id__in=claimed_policy_ids
).order_by(
    'policy_number'
)
    # --------------------------------------------------------
    # Get claims submitted by the logged-in policyholder
    # --------------------------------------------------------

    claims = Claim.objects.filter(
        policyholder=request.user
    ).select_related(
        'policy'
    ).order_by(
        '-created_at'
    )

    # --------------------------------------------------------
    # Send both policies and claims to the template
    # --------------------------------------------------------

    return render(
        request,
        'my-claims.html',
        {
            'user': request.user,
            'policies': policies,
            'claims': claims
        }
    )

# ============================================================
# SUBMIT CLAIM
# ============================================================

def submit_claim(request):

    # --------------------------------------------------------
    # Check authentication
    # --------------------------------------------------------

    if not request.user.is_authenticated:
        return redirect('/')

    # --------------------------------------------------------
    # Get registered policies for logged-in user
    # --------------------------------------------------------

    claimed_policy_ids = Claim.objects.filter(
        policyholder=request.user
    ).values_list(
        'policy_id',
        flat=True
    )

    policies = Policy.objects.filter(
        policyholder=request.user
    ).exclude(
        id__in=claimed_policy_ids
    ).order_by(
        'policy_number'
    )

    previous_claims = Claim.objects.filter(
        policyholder=request.user
    ).count()

    # --------------------------------------------------------
    # GET: Check if a policy was selected from My Claims
    # --------------------------------------------------------

    selected_policy_id = request.GET.get('policy')

    # --------------------------------------------------------
    # POST: Submit claim
    # --------------------------------------------------------

    if request.method == 'POST':

        # ----------------------------------------------------
        # Get selected policy
        # ----------------------------------------------------

        policy_id = request.POST.get('policy_id')

        try:
            policy = Policy.objects.get(
                id=policy_id,
                policyholder=request.user
            )

        except (
            Policy.DoesNotExist,
            TypeError,
            ValueError
        ):

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Please select a valid registered policy.'
                }
            )

        # ----------------------------------------------------
        # Incident details
        # ----------------------------------------------------

        incident_date = request.POST.get(
            'incident_date',
            ''
        ).strip()

        incident_time = request.POST.get(
            'incident_time',
            ''
        ).strip()

        accident_type = request.POST.get(
            'accident_type',
            ''
        ).strip()

        accident_location = request.POST.get(
            'accident_location',
            ''
        ).strip()

        description = request.POST.get(
            'description',
            ''
        ).strip()

        # ----------------------------------------------------
        # Driver details
        # ----------------------------------------------------

        driver_name = request.POST.get(
            'driver_name',
            ''
        ).strip()

        # Automatically get driving license number
        # from registered user profile

        driving_license_number = (
            request.user.userprofile.driving_license_number
            or ''
        ).strip().upper()

        driver_age = request.POST.get(
            'driver_age',
            ''
        ).strip()
        try:
            driver_age_int = int(driver_age)
        except (ValueError, TypeError):
            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'previous_claims': previous_claims,
                    'error': 'Please enter a valid driver age.'
                }
    )

        if driver_age_int < 18 or driver_age_int > 80:
            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'previous_claims': previous_claims,
                    'error': 'Driver age must be between 18 and 80 years.'
                }
            )

        driver_authorised_value = request.POST.get(
            'driver_authorised',
            ''
        ).strip()

        driver_authorised = None

        if driver_authorised_value == 'Yes':
            driver_authorised = True

        elif driver_authorised_value == 'No':
            driver_authorised = False

        # ----------------------------------------------------
        # Third-party details
        # ----------------------------------------------------

        third_party_involved_value = request.POST.get(
            'third_party_involved',
            ''
        ).strip()

        third_party_injury_value = request.POST.get(
            'third_party_injury',
            ''
        ).strip()

        third_party_damage_value = request.POST.get(
            'third_party_damage',
            ''
        ).strip()

        third_party_involved = (
            third_party_involved_value == 'Yes'
        )

        third_party_injury = (
            third_party_injury_value == 'Yes'
        )

        third_party_damage = (
            third_party_damage_value == 'Yes'
        )

        # ----------------------------------------------------
        # Police / FIR details
        # ----------------------------------------------------

        police_report_status = request.POST.get(
            'police_report_status',
            ''
        ).strip()

        police_report_number = request.POST.get(
            'police_report_number',
            ''
        ).strip()

        police_station = request.POST.get(
            'police_station',
            ''
        ).strip()

        police_report_date = request.POST.get(
            'police_report_date',
            ''
        ).strip()

        police_not_reported_reason = request.POST.get(
            'police_not_reported_reason',
            ''
        ).strip()

        # ----------------------------------------------------
        # Claim / damage details
        # ----------------------------------------------------

        estimated_damage = request.POST.get(
            'estimated_damage',
            ''
        ).strip()

        claim_amount = request.POST.get(
            'claim_amount',
            ''
        ).strip()

        damage_description = request.POST.get(
            'damage_description',
            ''
        ).strip()

        damaged_parts = request.POST.getlist(
            'damaged_parts'
        )

        damaged_parts = ', '.join(
            damaged_parts
        )

        # ----------------------------------------------------
        # Basic validation
        # ----------------------------------------------------

        if not driver_name:

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        "Please enter the driver's name."
                }
            )

        if not driving_license_number:

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        "Please enter the driver's license number."
                }
            )

        if not driver_age:

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Please enter the driver age.'
                }
            )

        if not estimated_damage:

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Please enter the estimated damage.'
                }
            )

        if not claim_amount:

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Please enter the claim amount.'
                }
            )

        # ----------------------------------------------------
        # Convert numeric values
        # ----------------------------------------------------

        try:

            estimated_damage_float = float(
                estimated_damage
            )

        except (
            ValueError,
            TypeError
        ):

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Estimated damage must be a valid number.'
                }
            )

        try:

            claim_amount_float = float(
                claim_amount
            )

        except (
            ValueError,
            TypeError
        ):

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Claim amount must be a valid number.'
                }
            )

        if (
            estimated_damage_float < 0
            or claim_amount_float < 0
        ):

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Damage and claim amounts cannot be negative.'
                }
            )

        # ----------------------------------------------------
        # Convert incident date
        # ----------------------------------------------------

        incident_date_obj = None

        if incident_date:

            try:

                incident_date_obj = (
                    timezone.datetime.strptime(
                        incident_date,
                        '%Y-%m-%d'
                    ).date()
                )

            except ValueError:

                return render(
                    request,
                    'submit-claim.html',
                    {
                        'user': request.user,
                        'policies': policies,
                        'selected_policy_id': policy_id,
                        'previous_claims': previous_claims,
                        'error':
                            'Please enter a valid incident date.'
                    }
                )

        # ----------------------------------------------------
        # Incident Date Validation
        # Maximum one month in the past
        # Cannot be in the future
        # ----------------------------------------------------

        if incident_date_obj:

            today = timezone.localdate()

            minimum_incident_date = (
                today - relativedelta(months=1)
            )

            if incident_date_obj > today:

                return render(
                    request,
                    'submit-claim.html',
                    {
                        'user': request.user,
                        'policies': policies,
                        'selected_policy_id': policy_id,
                        'previous_claims': previous_claims,
                        'error':
                            'Incident date cannot be in the future.'
                    }
                )

            if (
                incident_date_obj
                < minimum_incident_date
            ):

                return render(
                    request,
                    'submit-claim.html',
                    {
                        'user': request.user,
                        'policies': policies,
                        'selected_policy_id': policy_id,
                        'previous_claims': previous_claims,
                        'error':
                            'Incident date cannot be more than one month old.'
                    }
                )

        # ----------------------------------------------------
        # Convert incident time
        # ----------------------------------------------------

        incident_time_obj = None

        if incident_time:

            try:

                incident_time_obj = (
                    timezone.datetime.strptime(
                        incident_time,
                        '%H:%M'
                    ).time()
                )

            except ValueError:

                return render(
                    request,
                    'submit-claim.html',
                    {
                        'user': request.user,
                        'policies': policies,
                        'selected_policy_id': policy_id,
                        'previous_claims': previous_claims,
                        'error':
                            'Please enter a valid incident time.'
                    }
                )

        # ----------------------------------------------------
        # Prevent duplicate claim submission
        # ----------------------------------------------------

        duplicate_claim = Claim.objects.filter(
            policyholder=request.user,
            policy=policy,
            incident_date=incident_date_obj,
            accident_type=accident_type,
            status__in=[
                'under_review',
                'investigation'
            ]
        ).first()

        if duplicate_claim:

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error': (
                        f'A claim for this incident has already '
                        f'been submitted as '
                        f'{duplicate_claim.claim_id}.'
                    )
                }
            )

        # ----------------------------------------------------
        # Convert police report date
        # ----------------------------------------------------

        police_report_date_obj = None

        if police_report_date:

            try:

                police_report_date_obj = (
                    timezone.datetime.strptime(
                        police_report_date,
                        '%Y-%m-%d'
                    ).date()
                )

            except ValueError:

                return render(
                    request,
                    'submit-claim.html',
                    {
                        'user': request.user,
                        'policies': policies,
                        'selected_policy_id': policy_id,
                        'previous_claims': previous_claims,
                        'error':
                            'Please enter a valid police report date.'
                    }
                )

        # ----------------------------------------------------
        # Police Report Date Validation
        # Maximum one month in the past
        # Cannot be in the future
        # ----------------------------------------------------

        if police_report_date_obj:

            today = timezone.localdate()

            minimum_report_date = (
                today - relativedelta(months=1)
            )

            if police_report_date_obj > today:

                return render(
                    request,
                    'submit-claim.html',
                    {
                        'user': request.user,
                        'policies': policies,
                        'selected_policy_id': policy_id,
                        'previous_claims': previous_claims,
                        'error':
                            'Report date cannot be in the future.'
                    }
                )

            if (
                police_report_date_obj
                < minimum_report_date
            ):

                return render(
                    request,
                    'submit-claim.html',
                    {
                        'user': request.user,
                        'policies': policies,
                        'selected_policy_id': policy_id,
                        'previous_claims': previous_claims,
                        'error':
                            'Report date cannot be more than one month old.'
                    }
                )

        # ----------------------------------------------------
        # Report Date Cannot Be Before Incident Date
        # ----------------------------------------------------

        if (
            incident_date_obj
            and police_report_date_obj
            and police_report_date_obj < incident_date_obj
        ):

            return render(
                request,
                'submit-claim.html',
                {
                    'user': request.user,
                    'policies': policies,
                    'selected_policy_id': policy_id,
                    'previous_claims': previous_claims,
                    'error':
                        'Report date cannot be before the incident date.'
                }
            )

        # ----------------------------------------------------
        # Calculate days to report
        # ----------------------------------------------------

        days_to_report = 0

        if incident_date_obj:

            days_to_report = (
                timezone.localdate()
                - incident_date_obj
            ).days

            if days_to_report < 0:
                days_to_report = 0

        # ----------------------------------------------------
        # Generate next Claim ID
        # ----------------------------------------------------

        last_claim = Claim.objects.order_by(
            '-id'
        ).first()

        if last_claim:

            try:

                last_number = int(
                    last_claim.claim_id.replace(
                        'CLM',
                        ''
                    )
                )

                next_number = (
                    last_number + 1
                )

            except (
                ValueError,
                AttributeError
            ):

                next_number = (
                    Claim.objects.count() + 1
                )

        else:

            next_number = 1

        claim_id = (
            f'CLM{next_number:03d}'
        )

        # ----------------------------------------------------
        # V3 ML prediction
        # ----------------------------------------------------

        (
            risk_level,
            ai_confidence,
            low_probability,
            medium_probability,
            high_probability
        ) = predict_claim_risk(

            accident_type=accident_type,

            driver_age=driver_age_int,

            previous_claims=previous_claims,

            days_to_report=days_to_report,

            police_report_status=
                police_report_status,

            driver_authorised=
                driver_authorised,

            third_party_involved=
                third_party_involved,

            third_party_injury=
                third_party_injury,

            third_party_damage=
                third_party_damage,

            estimated_damage=
                estimated_damage_float,

            claim_amount=
                claim_amount_float,

            insured_value=
                policy.insured_value
        )

        # ----------------------------------------------------
        # Find active claim officers
        # ----------------------------------------------------

        officers = User.objects.filter(
            userprofile__role='officer',
            is_active=True
        ).annotate(
            workload=Count(
                'assigned_claims'
            )
        ).order_by(
            'workload',
            'id'
        )

        # ----------------------------------------------------
        # Automatically assign officer
        # ----------------------------------------------------

        assigned_officer = (
            officers.first()
            if officers.exists()
            else None
        )

        # ----------------------------------------------------
        # Create claim
        # ----------------------------------------------------

        claim = Claim.objects.create(

            # Claim identification
            claim_id=claim_id,

            policyholder=request.user,

            # Registered policy
            policy=policy,

            # Policy details
            policy_number=policy.policy_number,

            policy_type=policy.coverage_type,

            # Vehicle details
            vehicle_make=policy.vehicle_make,

            vehicle_model=policy.vehicle_model,

            vehicle_year=policy.vehicle_year,

            registration_number=
                policy.registration_number,

            # Incident details
            incident_date=incident_date_obj,

            incident_time=incident_time_obj,

            accident_type=accident_type,

            accident_location=accident_location,

            description=description,

            # Police / FIR details
            police_report_status=
                police_report_status,

            police_report_number=
                police_report_number,

            police_station=
                police_station,

            police_report_date=
                police_report_date_obj,

            # Driver details
            driver_name=driver_name,

            driving_license_number=
                driving_license_number,

            driver_age=driver_age_int,

            driver_authorised=
                driver_authorised,

            # Third-party details
            third_party_involved=
                third_party_involved,

            third_party_injury=
                third_party_injury,

            third_party_damage=
                third_party_damage,

            # Claim / damage details
            estimated_damage=
                estimated_damage,

            claim_amount=
                claim_amount,

            damaged_parts=
                damaged_parts,

            damage_description=
                damage_description,

            police_not_reported_reason=
                police_not_reported_reason,

            previous_claims=
                previous_claims,

            days_to_report=
                days_to_report,

            # ML prediction
            risk_level=
                risk_level,

            ai_confidence=
                ai_confidence,

            low_probability=
                low_probability,

            medium_probability=
                medium_probability,

            high_probability=
                high_probability,

            # Initial status
            status='under_review',

            # Automatic officer assignment
            assigned_officer=
                assigned_officer
        )

        # ----------------------------------------------------
        # Save supporting documents
        # and generate AI summaries
        # ----------------------------------------------------

        documents = {

            'driving_license':
                request.FILES.get(
                    'driving_license'
                ),

            'vehicle_registration':
                request.FILES.get(
                    'vehicle_registration'
                ),

            'insurance_policy':
                request.FILES.get(
                    'insurance_policy'
                ),

            'repair_estimate':
                request.FILES.get(
                    'repair_estimate'
                ),

            'police_report':
                request.FILES.get(
                    'police_report_document'
                ),
        }
        ALLOWED_EXTENSIONS = ('.pdf', '.png', '.jpg', '.jpeg', '.docx')
        MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

        for doc_type, file_obj in documents.items():
            if file_obj:
                if not file_obj.name.lower().endswith(ALLOWED_EXTENSIONS):
                    return render(request, 'submit-claim.html', {'error': f'{file_obj.name} has an unsupported file format.'})
            if file_obj and file_obj.size > MAX_FILE_SIZE:
                return render(
        request,
        'submit-claim.html',
        {'error': f'{file_obj.name} exceeds 5MB limit.'}
    )
        

        for (
            document_type,
            uploaded_file
        ) in documents.items():

            if uploaded_file:

                document_record = (
                    ClaimDocument.objects.create(
                        claim=claim,
                        document_type=document_type,
                        file=uploaded_file
                    )
                )

                # ------------------------------------------------
                # Generate document summary
                # ------------------------------------------------

                try:

                    (
                        extracted_text,
                        ai_summary
                    ) = process_document(
                        document_record.file.path
                    )

                    document_record.extracted_text = (
                        extracted_text
                    )

                    document_record.ai_summary = (
                        ai_summary
                    )

                    document_record.save(
                        update_fields=[
                            'extracted_text',
                            'ai_summary'
                        ]
                    )

                except Exception as error:

                    print(
                        'Document processing error:',
                        error
                    )

                    document_record.ai_summary = (
                        'The document was uploaded successfully, '
                        'but readable text could not be processed. '
                        'Please review the original document.'
                    )

                    document_record.save(
                        update_fields=[
                            'ai_summary'
                        ]
                    )

        # ----------------------------------------------------
        # Claim submitted successfully
        # ----------------------------------------------------

        return redirect(
            '/my-claims/'
        )

    # --------------------------------------------------------
    # GET: Show claim form
    # --------------------------------------------------------

    return render(
        request,
        'submit-claim.html',
        {
            'user': request.user,
            'policies': policies,
            'selected_policy_id':
                selected_policy_id,
            'previous_claims':
                previous_claims
        }
    )
# ============================================================
# CLAIM DETAILS - POLICYHOLDER
# ============================================================

def claim_details(request, claim_id):

    if not request.user.is_authenticated:
        return redirect('/')

    try:

        claim = Claim.objects.get(
            claim_id=claim_id,
            policyholder=request.user
        )

    except Claim.DoesNotExist:

        return redirect('/my-claims/')

    documents = ClaimDocument.objects.filter(
        claim=claim
    )

    return render(
        request,
        'claim-details.html',
        {
            'user': request.user,
            'claim': claim,
            'documents': documents
        }
    )


# ============================================================
# PROFILE
# ============================================================

def profile(request):

    if not request.user.is_authenticated:
        return redirect('/')

    try:

        user_profile = UserProfile.objects.get(
            user=request.user
        )

    except UserProfile.DoesNotExist:

        user_profile = None

    return render(
        request,
        'profile.html',
        {
            'user': request.user,
            'profile': user_profile
        }
    )


# ============================================================
# PASSWORD CHANGE
# ============================================================

# ============================================================
# PASSWORD CHANGE
# ============================================================

def password_change(request):

    if not request.user.is_authenticated:
        return redirect('/')


    # --------------------------------------------------------
    # Get logged-in user's profile
    # --------------------------------------------------------

    try:

        user_profile = UserProfile.objects.get(
            user=request.user
        )

    except UserProfile.DoesNotExist:

        user_profile = None


    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == 'POST':

        current_password = request.POST.get(
            'current_password',
            ''
        )

        new_password = request.POST.get(
            'new_password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )


        # ----------------------------------------------------
        # Check current password
        # ----------------------------------------------------

        if not request.user.check_password(
            current_password
        ):

            return render(
                request,
                'password-change.html',
                {
                    'user': request.user,
                    'profile': user_profile,
                    'error':
                        'Current password is incorrect.'
                }
            )


        # ----------------------------------------------------
        # Check new passwords
        # ----------------------------------------------------

        if new_password != confirm_password:

            return render(
                request,
                'password-change.html',
                {
                    'user': request.user,
                    'profile': user_profile,
                    'error':
                        'New passwords do not match.'
                }
            )


        # ----------------------------------------------------
        # Check password length
        # ----------------------------------------------------

        if len(new_password) < 8:

            return render(
                request,
                'password-change.html',
                {
                    'user': request.user,
                    'profile': user_profile,
                    'error':
                        'Password must be at least 8 characters long.'
                }
            )


        # ----------------------------------------------------
        # Change password
        # ----------------------------------------------------

        request.user.set_password(
            new_password
        )

        request.user.save()


        # Keep the current user logged in
        update_session_auth_hash(
            request,
            request.user
        )


        # ----------------------------------------------------
        # Return to profile
        # ----------------------------------------------------

        return redirect('/profile/')


    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        'password-change.html',
        {
            'user': request.user,
            'profile': user_profile
        }
    )
# ============================================================
# OFFICER ACCESS CHECK
# ============================================================

def is_officer(request):

    if not request.user.is_authenticated:
        return False

    try:

        profile = UserProfile.objects.get(
            user=request.user
        )

        return profile.role == 'officer'

    except UserProfile.DoesNotExist:

        return False


# ============================================================
# OFFICER DASHBOARD
# ============================================================

def officer_dashboard(request):

    if not is_officer(request):

        if not request.user.is_authenticated:
            return redirect('/')

        return redirect('/dashboard/')

    # --------------------------------------------------------
    # Get only claims assigned to the logged-in officer
    # --------------------------------------------------------

    claims = Claim.objects.filter(
        assigned_officer=request.user
    ).order_by(
        '-created_at'
    )

    # --------------------------------------------------------
    # Claim Statistics
    # --------------------------------------------------------

    total_claims = claims.count()

    pending_claims = claims.filter(
        status='under_review'
    ).count()

    approved_claims = claims.filter(
        status='approved'
    ).count()

    rejected_claims = claims.filter(
        status='rejected'
    ).count()

    investigation_claims = claims.filter(
        status='investigation'
    ).count()

    # --------------------------------------------------------
    # Render Officer Dashboard
    # --------------------------------------------------------

    return render(
        request,
        'officer-dashboard.html',
        {
            'user': request.user,
            'claims': claims,

            'total_claims': total_claims,

            'pending_claims': pending_claims,

            'approved_claims':
                approved_claims,

            'rejected_claims':
                rejected_claims,

            'investigation_claims':
                investigation_claims,
        }
    )


# ============================================================
# OFFICER CLAIMS
# ============================================================

def officer_claims(request):

    if not is_officer(request):

        if not request.user.is_authenticated:
            return redirect('/')

        return redirect('/dashboard/')

    claims = Claim.objects.all().order_by(
        '-created_at'
    )

    return render(
        request,
        'officer-claims.html',
        {
            'user': request.user,
            'claims': claims
        }
    )


# ============================================================
# OFFICER PENDING CLAIMS
# ============================================================

def officer_pending(request):

    if not is_officer(request):

        if not request.user.is_authenticated:
            return redirect('/')

        return redirect('/dashboard/')

    pending_claims = Claim.objects.filter(
        status='under_review'
    ).order_by(
        '-created_at'
    )

    total_pending = pending_claims.count()

    medium_risk_claims = pending_claims.filter(
        risk_level='medium'
    ).count()

    high_risk_claims = pending_claims.filter(
        risk_level='high'
    ).count()

    return render(
        request,
        'officer-pending.html',
        {
            'user': request.user,
            'claims': pending_claims,
            'pending_claims':
                total_pending,
            'medium_risk_claims':
                medium_risk_claims,
            'high_risk_claims':
                high_risk_claims,
        }
    )


# ============================================================
# OFFICER CLAIM REVIEW
# ============================================================

def officer_claim_review(request, claim_id):

    if not is_officer(request):

        if not request.user.is_authenticated:
            return redirect('/')

        return redirect('/dashboard/')

    try:

        claim = Claim.objects.get(
            claim_id=claim_id
        )

    except Claim.DoesNotExist:

        return redirect('/officer-claims/')

    documents = ClaimDocument.objects.filter(
        claim=claim
    )

    ai_explanation = generate_claim_explanation(claim)

    return render(
        request,
        'officer-claim-review.html',
        {
            'user': request.user,
            'claim': claim,
            'documents': documents,
            'ai_explanation': ai_explanation
        }
    )


# ============================================================
# OFFICER CLAIM DECISION
# ============================================================

def officer_claim_decision(request, claim_id):

    if not is_officer(request):

        if not request.user.is_authenticated:
            return redirect('/')

        return redirect('/dashboard/')

    try:

        claim = Claim.objects.get(
            claim_id=claim_id
        )

    except Claim.DoesNotExist:

        return redirect('/officer-claims/')

    if request.method != 'POST':

        return redirect(
            f'/officer-claim/{claim.claim_id}/'
        )

    decision = request.POST.get(
        'decision'
    )

    remarks = request.POST.get(
        'officer_remarks',
        ''
    ).strip()

    valid_decisions = [
        'approved',
        'rejected',
        'investigation'
    ]

    if decision not in valid_decisions:

        documents = ClaimDocument.objects.filter(
            claim=claim
        )

        return render(
            request,
            'officer-claim-review.html',
            {
                'user': request.user,
                'claim': claim,
                'documents': documents,
                'error':
                    'Please select a valid decision.'
            }
        )

    claim.status = decision

    claim.officer_decision = decision

    claim.officer_remarks = remarks

    claim.reviewed_by = request.user

    claim.reviewed_at = timezone.now()

    claim.save()

    return redirect(
        f'/officer-claim/{claim.claim_id}/'
    )


# ============================================================
# OFFICER REPORTS
# ============================================================

def officer_reports(request):

    if not is_officer(request):

        if not request.user.is_authenticated:
            return redirect('/')

        return redirect('/dashboard/')

    total_claims = Claim.objects.count()

    processed_claims = Claim.objects.filter(
        status__in=[
            'approved',
            'rejected'
        ]
    ).count()

    pending_claims = Claim.objects.filter(
        status='under_review'
    ).count()

    approved_claims = Claim.objects.filter(
        status='approved'
    ).count()

    rejected_claims = Claim.objects.filter(
        status='rejected'
    ).count()

    investigation_claims = Claim.objects.filter(
        status='investigation'
    ).count()

    low_risk = Claim.objects.filter(
        risk_level='low'
    ).count()

    medium_risk = Claim.objects.filter(
        risk_level='medium'
    ).count()

    high_risk = Claim.objects.filter(
        risk_level='high'
    ).count()

    approved_percentage = 0
    pending_percentage = 0
    rejected_percentage = 0
    high_risk_percentage = 0

    if total_claims > 0:

        approved_percentage = round(
            (approved_claims / total_claims) * 100
        )

        pending_percentage = round(
            (pending_claims / total_claims) * 100
        )

        rejected_percentage = round(
            (rejected_claims / total_claims) * 100
        )

        high_risk_percentage = round(
            (high_risk / total_claims) * 100
        )

    return render(
        request,
        'officer-reports.html',
        {
            'user': request.user,
            'total_claims': total_claims,
            'processed_claims': processed_claims,
            'pending_claims': pending_claims,
            'approved_claims': approved_claims,
            'rejected_claims': rejected_claims,
            'investigation_claims': investigation_claims,
            'low_risk': low_risk,
            'medium_risk': medium_risk,
            'high_risk': high_risk,
            'approved_percentage': approved_percentage,
            'pending_percentage': pending_percentage,
            'rejected_percentage': rejected_percentage,
            'high_risk_percentage': high_risk_percentage,
        }
    )


# ============================================================
# ADMINISTRATOR ACCESS CHECK
# ============================================================

def is_admin(request):

    if not request.user.is_authenticated:
        return False

    try:

        profile = UserProfile.objects.get(
            user=request.user
        )

        return profile.role == 'admin'

    except UserProfile.DoesNotExist:

        return False


# ============================================================
# ADMIN DASHBOARD
# ============================================================

def admin_dashboard(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    total_users = User.objects.count()

    total_policyholders = UserProfile.objects.filter(
        role='policyholder'
    ).count()

    total_officers = UserProfile.objects.filter(
        role='officer'
    ).count()

    total_admins = UserProfile.objects.filter(
        role='admin'
    ).count()

    total_plans = InsurancePlan.objects.count()

    total_claims = Claim.objects.count()

    pending_claims = Claim.objects.filter(
        status='under_review'
    ).count()

    approved_claims = Claim.objects.filter(
        status='approved'
    ).count()

    rejected_claims = Claim.objects.filter(
        status='rejected'
    ).count()

    investigation_claims = Claim.objects.filter(
        status='investigation'
    ).count()

    low_risk_claims = Claim.objects.filter(
        risk_level='low'
    ).count()

    medium_risk_claims = Claim.objects.filter(
        risk_level='medium'
    ).count()

    high_risk_claims = Claim.objects.filter(
        risk_level='high'
    ).count()

    recent_claims = Claim.objects.select_related(
        'policyholder',
        'assigned_officer',
        'reviewed_by'
    ).order_by(
        '-created_at'
    )[:10]

    return render(
        request,
        'admin-dashboard.html',
        {
            'user': request.user,

            'total_users': total_users,
            'total_policyholders': total_policyholders,
            'total_officers': total_officers,
            'total_admins': total_admins,
            'total_plans': total_plans,

            'total_claims': total_claims,
            'pending_claims': pending_claims,
            'approved_claims': approved_claims,
            'rejected_claims': rejected_claims,
            'investigation_claims':
                investigation_claims,

            'low_risk_claims': low_risk_claims,
            'medium_risk_claims': medium_risk_claims,
            'high_risk_claims': high_risk_claims,

            'recent_claims': recent_claims,
        }
    )

# ============================================================
# ADMIN - POLICYHOLDERS
# ============================================================

def admin_policyholders(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    # --------------------------------------------------------
    # Get all policyholders
    # --------------------------------------------------------

    policyholders = User.objects.filter(
        userprofile__role='policyholder'
    ).order_by(
        'email'
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    total_policyholders = policyholders.count()

    active_policyholders = policyholders.filter(
        is_active=True
    ).count()

    inactive_policyholders = policyholders.filter(
        is_active=False
    ).count()

    # --------------------------------------------------------
    # Get policies and claims for each policyholder
    # --------------------------------------------------------

    for policyholder in policyholders:

        policyholder.customer_policies = Policy.objects.filter(
            policyholder=policyholder
        ).order_by(
            '-start_date'
        )

        policyholder.customer_claims = Claim.objects.filter(
            policyholder=policyholder
        ).select_related(
            'policy'
        ).order_by(
            '-created_at'
        )

        # Counts

        policyholder.policy_count = (
            policyholder.customer_policies.count()
        )

        policyholder.claim_count = (
            policyholder.customer_claims.count()
        )

        # Active policies

        policyholder.active_policy_count = (
            policyholder.customer_policies.filter(
                status='active'
            ).count()
        )

        # Claim statistics

        policyholder.approved_claim_count = (
            policyholder.customer_claims.filter(
                status='approved'
            ).count()
        )

        policyholder.pending_claim_count = (
            policyholder.customer_claims.filter(
                status='under_review'
            ).count()
        )

        policyholder.rejected_claim_count = (
            policyholder.customer_claims.filter(
                status='rejected'
            ).count()
        )

    # --------------------------------------------------------
    # Render page
    # --------------------------------------------------------

    return render(
        request,
        'admin-policyholders.html',
        {
            'user': request.user,

            'policyholders': policyholders,

            'total_policyholders':
                total_policyholders,

            'active_policyholders':
                active_policyholders,

            'inactive_policyholders':
                inactive_policyholders,
        }
    )

def admin_officers(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    officers = User.objects.filter(
        userprofile__role='officer'
    ).annotate(
        assigned_claim_count=Count(
            'assigned_claims'
        ),
        approved_claim_count=Count(
            'assigned_claims',
            filter=Q(
                assigned_claims__status='approved'
            )
        ),
        rejected_claim_count=Count(
            'assigned_claims',
            filter=Q(
                assigned_claims__status='rejected'
            )
        )
    ).order_by(
        'first_name',
        'last_name'
    )

    total_officers = officers.count()

    active_officers = officers.filter(
        is_active=True
    ).count()

    inactive_officers = officers.filter(
        is_active=False
    ).count()

    return render(
        request,
        'admin-officers.html',
        {
            'user': request.user,

            'officers': officers,

            'total_officers': total_officers,
            'active_officers': active_officers,
            'inactive_officers': inactive_officers,
        }
    )

def admin_edit_officer(request, officer_id):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    officer = get_object_or_404(
        User,
        id=officer_id,
        userprofile__role='officer'
    )

    if request.method == 'POST':

        new_email = request.POST.get(
            'email',
            ''
        ).strip()

        officer.first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        officer.last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        officer.email = new_email

        # Keep username synchronized with email
        officer.username = new_email

        officer.save()

        return redirect('/admin-officers/')

    return render(
        request,
        'admin-edit-officer.html',
        {
            'user': request.user,
            'officer': officer,
        }
    )


def admin_toggle_officer(request, officer_id):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    officer = get_object_or_404(
        User,
        id=officer_id,
        userprofile__role='officer'
    )

    officer.is_active = not officer.is_active
    officer.save()

    return redirect('/admin-officers/')

# ============================================================
# ADMIN - POLICYHOLDER DETAILS
# ============================================================
def admin_policyholder_details(request, user_id):

    if not request.user.is_authenticated:
        return redirect('login')

    # Get the selected policyholder
    policyholder = get_object_or_404(
        User,
        id=user_id
    )

    # Get this customer's policies
    policies = Policy.objects.filter(
        policyholder=policyholder
    )

    # Get this customer's claims
    claims = Claim.objects.filter(
        policyholder=policyholder
    )

    # Count approved claims
    approved_claims = claims.filter(
        status='approved'
    ).count()

    # Count pending/under-review claims
    pending_claims = claims.filter(
        status='under_review'
    ).count()

    context = {
        'policyholder': policyholder,
        'policies': policies,
        'claims': claims,
        'approved_claims': approved_claims,
        'pending_claims': pending_claims,
    }

    return render(
        request,
        'admin-policyholder-details.html',
        context
    )

# ============================================================
# ADMIN - ALL CLAIMS
# ============================================================

def admin_claims(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    claims = Claim.objects.select_related(
        'policyholder',
        'reviewed_by',
        'assigned_officer'
    ).order_by(
        '-created_at'
    )

    total_claims = claims.count()

    pending_claims = claims.filter(
        status='under_review'
    ).count()

    approved_claims = claims.filter(
        status='approved'
    ).count()

    rejected_claims = claims.filter(
        status='rejected'
    ).count()

    investigation_claims = claims.filter(
        status='investigation'
    ).count()

    return render(
        request,
        'admin-claims.html',
        {
            'user': request.user,
            'claims': claims,
            'total_claims': total_claims,
            'pending_claims': pending_claims,
            'approved_claims': approved_claims,
            'rejected_claims': rejected_claims,
            'investigation_claims': investigation_claims,
        }
    )


# ============================================================
# ADMIN - CLAIM DETAILS
# ============================================================

def admin_claim_details(request, claim_id):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    try:

        claim = Claim.objects.select_related(
            'policyholder',
            'reviewed_by',
            'assigned_officer'
        ).get(
            claim_id=claim_id
        )

    except Claim.DoesNotExist:

        return redirect('/admin-claims/')

    documents = ClaimDocument.objects.filter(
        claim=claim
    )

    officers = User.objects.filter(
        userprofile__role='officer',
        is_active=True
    ).order_by(
        'email'
    )

    return render(
        request,
        'admin-claim-details.html',
        {
            'user': request.user,
            'claim': claim,
            'documents': documents,
            'officers': officers,
        }
    )


# ============================================================
# ADMIN - ASSIGN CLAIM OFFICER
# ============================================================

def admin_assign_claim_officer(request, claim_id):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    if request.method != 'POST':

        return redirect(
            f'/admin-claim/{claim_id}/'
        )

    try:

        claim = Claim.objects.get(
            claim_id=claim_id
        )

    except Claim.DoesNotExist:

        return redirect('/admin-claims/')

    officer_id = request.POST.get(
        'assigned_officer'
    )

    try:

        officer = User.objects.get(
            id=officer_id,
            userprofile__role='officer',
            is_active=True
        )

    except (User.DoesNotExist, TypeError, ValueError):

        return redirect(
            f'/admin-claim/{claim_id}/'
        )

    claim.assigned_officer = officer

    claim.save(
        update_fields=['assigned_officer']
    )

    return redirect(
        f'/admin-claim/{claim_id}/'
    )
# ============================================================
# ADMIN - REPORTS
# ============================================================
def admin_reports(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    # ========================================================
    # BASIC CLAIM QUERYSETS
    # ========================================================

    all_claims = Claim.objects.all()

    total_claims = all_claims.count()

    approved_claims = all_claims.filter(
        status='approved'
    ).count()

    rejected_claims = all_claims.filter(
        status='rejected'
    ).count()

    pending_claims = all_claims.filter(
        status='under_review'
    ).count()

    investigation_claims = all_claims.filter(
        status='investigation'
    ).count()


    # ========================================================
    # CLAIM STATUS PERCENTAGES
    # ========================================================

    approved_percentage = 0
    rejected_percentage = 0
    pending_percentage = 0
    investigation_percentage = 0

    if total_claims > 0:

        approved_percentage = round(
            (approved_claims / total_claims) * 100,
            1
        )

        rejected_percentage = round(
            (rejected_claims / total_claims) * 100,
            1
        )

        pending_percentage = round(
            (pending_claims / total_claims) * 100,
            1
        )

        investigation_percentage = round(
            (investigation_claims / total_claims) * 100,
            1
        )


    # ========================================================
    # AI RISK COUNTS
    # ========================================================

    low_risk = all_claims.filter(
        risk_level='low'
    ).count()

    medium_risk = all_claims.filter(
        risk_level='medium'
    ).count()

    high_risk = all_claims.filter(
        risk_level='high'
    ).count()


    # ========================================================
    # AI RISK PERCENTAGES
    # ========================================================

    low_risk_percentage = 0
    medium_risk_percentage = 0
    high_risk_percentage = 0

    if total_claims > 0:

        low_risk_percentage = round(
            (low_risk / total_claims) * 100,
            1
        )

        medium_risk_percentage = round(
            (medium_risk / total_claims) * 100,
            1
        )

        high_risk_percentage = round(
            (high_risk / total_claims) * 100,
            1
        )

    location_counts = (
    Claim.objects
    .exclude(accident_location__isnull=True)
    .exclude(accident_location__exact='')
    .values('accident_location')
    .annotate(total=Count('id'))
    .order_by('-total')[:10]
)
    location_chart_labels = [
    item['accident_location']
    for item in location_counts
]
    location_chart_data = [
    item['total']
    for item in location_counts
]
    # ========================================================
    # ACCIDENT TYPE ANALYTICS
    # ========================================================

    accident_type_data = {}

    accident_types = all_claims.values_list(
        'accident_type',
        flat=True
    )

    for accident_type in accident_types:

        if accident_type:

            accident_type_data[accident_type] = (
                accident_type_data.get(
                    accident_type,
                    0
                ) + 1
            )


    accident_type_labels = list(
        accident_type_data.keys()
    )

    accident_type_values = list(
        accident_type_data.values()
    )


    # ========================================================
    # CLAIMS BY MONTH
    # ========================================================

    from django.db.models.functions import TruncMonth

    monthly_claims = (
        all_claims
        .filter(created_at__isnull=False)
        .annotate(
            month=TruncMonth(
                'created_at'
            )
        )
        .values('month')
        .annotate(
            total=Count('id')
        )
        .order_by('month')
    )


    month_labels = []

    month_values = []

    for item in monthly_claims:

        if item['month']:

            month_labels.append(
                item['month'].strftime(
                    '%b %Y'
                )
            )

            month_values.append(
                item['total']
            )


    # ========================================================
    # FINANCIAL ANALYTICS
    # ========================================================

    total_premiums = 0

    policies = Policy.objects.select_related(
        'insurance_plan'
    )


    for policy in policies:

        if policy.insurance_plan:

            if policy.insurance_plan.premium:

                total_premiums += (
                    policy.insurance_plan.premium
                )


    # --------------------------------------------------------
    # Total claim amount
    # --------------------------------------------------------

    total_claim_amount = 0

    claim_amounts = all_claims.filter(
        claim_amount__isnull=False
    )


    for claim in claim_amounts:

        total_claim_amount += (
            claim.claim_amount
        )


    # --------------------------------------------------------
    # Total estimated damage
    # --------------------------------------------------------

    total_estimated_damage = 0

    damage_claims = all_claims.filter(
        estimated_damage__isnull=False
    )


    for claim in damage_claims:

        total_estimated_damage += (
            claim.estimated_damage
        )


    # --------------------------------------------------------
    # Approved payout
    # --------------------------------------------------------

    total_claim_payouts = 0

    approved_amounts = all_claims.filter(
        status='approved',
        claim_amount__isnull=False
    )


    for claim in approved_amounts:

        total_claim_payouts += (
            claim.claim_amount
        )


    # --------------------------------------------------------
    # Pending claim amount
    # --------------------------------------------------------

    pending_claim_amount = 0

    pending_amounts = all_claims.filter(
        status__in=[
            'under_review',
            'investigation'
        ],
        claim_amount__isnull=False
    )


    for claim in pending_amounts:

        pending_claim_amount += (
            claim.claim_amount
        )


    # --------------------------------------------------------
    # Average claim amount
    # --------------------------------------------------------

    average_claim_amount = 0

    if total_claims > 0:

        average_claim_amount = (
            total_claim_amount /
            total_claims
        )


    # ========================================================
    # OFFICER PERFORMANCE
    # ========================================================

    officers = User.objects.filter(
        userprofile__role='officer'
    ).order_by(
        'email'
    )


    for officer in officers:

        # ----------------------------------------------------
        # Assigned claims
        # ----------------------------------------------------

        officer.assigned_claims_count = (
            Claim.objects.filter(
                assigned_officer=officer
            ).count()
        )


        # ----------------------------------------------------
        # Reviewed claims
        # ----------------------------------------------------

        officer.reviewed_claims_count = (
            Claim.objects.filter(
                reviewed_by=officer,
                reviewed_at__isnull=False
            ).count()
        )


        # ----------------------------------------------------
        # Pending claims
        # ----------------------------------------------------

        officer.pending_claims_count = (
            Claim.objects.filter(
                assigned_officer=officer,
                status='under_review'
            ).count()
        )


        # ----------------------------------------------------
        # Approved claims
        # ----------------------------------------------------

        officer.approved_claims_count = (
            Claim.objects.filter(
                reviewed_by=officer,
                status='approved'
            ).count()
        )


        # ----------------------------------------------------
        # Rejected claims
        # ----------------------------------------------------

        officer.rejected_claims_count = (
            Claim.objects.filter(
                reviewed_by=officer,
                status='rejected'
            ).count()
        )


        # ----------------------------------------------------
        # Average processing time
        # ----------------------------------------------------

        reviewed_claims = Claim.objects.filter(
            reviewed_by=officer,
            reviewed_at__isnull=False,
            created_at__isnull=False
        )


        total_processing_seconds = 0
        processing_count = 0


        for claim in reviewed_claims:

            processing_time = (
                claim.reviewed_at -
                claim.created_at
            )


            total_processing_seconds += (
                processing_time.total_seconds()
            )


            processing_count += 1


        if processing_count > 0:

            average_seconds = (
                total_processing_seconds /
                processing_count
            )


            average_days = (
                average_seconds /
                (24 * 60 * 60)
            )


            officer.average_processing_days = round(
                average_days,
                1
            )

        else:

            officer.average_processing_days = 0


    # ========================================================
    # SUSPICIOUS CLAIMS
    # ========================================================

    high_risk_claims = all_claims.filter(
        risk_level='high'
    ).select_related(
        'policyholder',
        'policy'
    ).order_by(
        '-created_at'
    )


    investigation_claims_list = all_claims.filter(
        status='investigation'
    ).select_related(
        'policyholder',
        'policy'
    ).order_by(
        '-created_at'
    )


    suspicious_claims = all_claims.filter(
        models.Q(
            risk_level='high'
        )
        |
        models.Q(
            status='investigation'
        )
        |
        models.Q(
            claim_amount__gt=models.F(
                'estimated_damage'
            )
        )
    ).select_related(
        'policyholder',
        'policy'
    ).distinct().order_by(
        '-created_at'
    )


    suspicious_claims_count = (
        suspicious_claims.count()
    )


    # ========================================================
    # RECENT CLAIMS
    # ========================================================

    recent_claims = (
        all_claims
        .select_related(
            'policyholder',
            'policy'
        )
        .order_by(
            '-created_at'
        )[:10]
    )


    # ========================================================
    # CHART DATA
    # ========================================================

    import json

    risk_chart_data = json.dumps([
        low_risk,
        medium_risk,
        high_risk
    ])


    status_chart_data = json.dumps([
        approved_claims,
        rejected_claims,
        pending_claims,
        investigation_claims
    ])


    accident_chart_labels = json.dumps(
        accident_type_labels
    )

    accident_chart_data = json.dumps(
        accident_type_values
    )

    month_chart_labels = json.dumps(
        month_labels
    )

    month_chart_data = json.dumps(
        month_values
    )


    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        'admin-reports.html',
        {

            'user':
                request.user,


            # ==================================================
            # CLAIM STATISTICS
            # ==================================================

            'total_claims':
                total_claims,

            'approved_claims':
                approved_claims,

            'rejected_claims':
                rejected_claims,

            'pending_claims':
                pending_claims,

            'investigation_claims':
                investigation_claims,


            # ==================================================
            # STATUS PERCENTAGES
            # ==================================================

            'approved_percentage':
                approved_percentage,

            'rejected_percentage':
                rejected_percentage,

            'pending_percentage':
                pending_percentage,

            'investigation_percentage':
                investigation_percentage,


            # ==================================================
            # RISK
            # ==================================================

            'low_risk':
                low_risk,

            'medium_risk':
                medium_risk,

            'high_risk':
                high_risk,

            'low_risk_percentage':
                low_risk_percentage,

            'medium_risk_percentage':
                medium_risk_percentage,

            'high_risk_percentage':
                high_risk_percentage,


            # ==================================================
            # FINANCIAL
            # ==================================================

            'total_premiums':
                total_premiums,

            'total_claim_amount':
                total_claim_amount,

            'total_estimated_damage':
                total_estimated_damage,

            'total_claim_payouts':
                total_claim_payouts,

            'pending_claim_amount':
                pending_claim_amount,

            'average_claim_amount':
                average_claim_amount,


            # ==================================================
            # CHART DATA
            # ==================================================

            'risk_chart_data':
                risk_chart_data,

            'status_chart_data':
                status_chart_data,

            'accident_chart_labels':
                accident_chart_labels,

            'accident_chart_data':
                accident_chart_data,

            'month_chart_labels':
                month_chart_labels,

            'month_chart_data':
                month_chart_data,

            'location_chart_labels': json.dumps(location_chart_labels),
            'location_chart_data': json.dumps(location_chart_data),


            # ==================================================
            # OFFICERS
            # ==================================================

            'officers':
                officers,


            # ==================================================
            # SUSPICIOUS CLAIMS
            # ==================================================

            'high_risk_claims':
                high_risk_claims,

            'investigation_claims_list':
                investigation_claims_list,

            'suspicious_claims':
                suspicious_claims,

            'suspicious_claims_count':
                suspicious_claims_count,


            # ==================================================
            # RECENT CLAIMS
            # ==================================================

            'recent_claims':
                recent_claims,

        }
    )
# ============================================================
# ADMIN - INSURANCE PLANS
# ============================================================

def admin_insurance_plans(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    plans = InsurancePlan.objects.all().order_by(
        'premium'
    )

    total_plans = plans.count()

    active_plans = plans.filter(
        is_active=True
    ).count()

    inactive_plans = plans.filter(
        is_active=False
    ).count()

    return render(
        request,
        'admin-insurance-plans.html',
        {
            'user': request.user,
            'plans': plans,
            'total_plans': total_plans,
            'active_plans': active_plans,
            'inactive_plans': inactive_plans,
        }
    )


# ============================================================
# ADMIN - EDIT INSURANCE PLAN
# ============================================================

def admin_edit_insurance_plan(
    request,
    plan_id
):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    plan = get_object_or_404(
        InsurancePlan,
        id=plan_id
    )

    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        plan_type = request.POST.get(
            'plan_type',
            ''
        ).strip()

        description = request.POST.get(
            'description',
            ''
        ).strip()

        insured_value = request.POST.get(
            'insured_value',
            ''
        ).strip()

        premium = request.POST.get(
            'premium',
            ''
        ).strip()

        duration_years = request.POST.get(
            'duration_years',
            ''
        ).strip()

        is_active = request.POST.get(
            'is_active'
        )

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not name:

            return render(
                request,
                'admin-edit-insurance-plan.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter the plan name.'
                }
            )

        if not plan_type:

            return render(
                request,
                'admin-edit-insurance-plan.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please select the plan type.'
                }
            )

        if not premium:

            return render(
                request,
                'admin-edit-insurance-plan.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter the premium amount.'
                }
            )

        # ----------------------------------------------------
        # Premium
        # ----------------------------------------------------

        try:

            premium_value = float(
                premium
            )

            if premium_value <= 0:

                raise ValueError

        except (ValueError, TypeError):

            return render(
                request,
                'admin-edit-insurance-plan.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Premium must be a valid amount greater than 0.'
                }
            )

        # ----------------------------------------------------
        # Insured Value
        # ----------------------------------------------------

        insured_value_final = None

        if insured_value:

            try:

                insured_value_final = float(
                    insured_value
                )

                if insured_value_final <= 0:

                    raise ValueError

            except (ValueError, TypeError):

                return render(
                    request,
                    'admin-edit-insurance-plan.html',
                    {
                        'user': request.user,
                        'plan': plan,
                        'error':
                            'Insured value must be a valid amount greater than 0.'
                    }
                )

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------

        if not duration_years:

            duration_years = 1

        try:

            duration_value = int(
                duration_years
            )

            if duration_value <= 0:

                raise ValueError

        except (ValueError, TypeError):

            return render(
                request,
                'admin-edit-insurance-plan.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Duration must be a valid number of years.'
                }
            )

        # ----------------------------------------------------
        # Update Insurance Plan
        # ----------------------------------------------------

        plan.name = name

        plan.plan_type = plan_type

        plan.description = (
            description
            if description
            else None
        )

        plan.insured_value = (
            insured_value_final
        )

        plan.premium = (
            premium_value
        )

        plan.duration_years = (
            duration_value
        )

        plan.is_active = (
            True
            if is_active == 'on'
            else False
        )

        plan.save()

        return redirect(
            '/admin-insurance-plans/'
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        'admin-edit-insurance-plan.html',
        {
            'user': request.user,
            'plan': plan
        }
    )
# ============================================================
# ADMIN - TOGGLE INSURANCE PLAN
# ============================================================

def admin_toggle_insurance_plan(
    request,
    plan_id
):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    plan = get_object_or_404(
        InsurancePlan,
        id=plan_id
    )

    plan.is_active = not plan.is_active

    plan.save(
        update_fields=['is_active']
    )

    return redirect(
        '/admin-insurance-plans/'
    )

# ============================================================
# ADMIN - ADD INSURANCE PLAN
# ============================================================

def admin_add_insurance_plan(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    if request.method == 'POST':

        name = request.POST.get(
            'name',
            ''
        ).strip()

        plan_type = request.POST.get(
            'plan_type',
            ''
        ).strip()

        description = request.POST.get(
            'description',
            ''
        ).strip()

        insured_value = request.POST.get(
            'insured_value',
            ''
        ).strip()

        premium = request.POST.get(
            'premium',
            ''
        ).strip()

        duration_years = request.POST.get(
            'duration_years',
            ''
        ).strip()

        is_active = request.POST.get(
            'is_active'
        )

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not name:

            return render(
                request,
                'admin-add-insurance-plan.html',
                {
                    'user': request.user,
                    'error':
                        'Please enter the plan name.'
                }
            )

        if not plan_type:

            return render(
                request,
                'admin-add-insurance-plan.html',
                {
                    'user': request.user,
                    'error':
                        'Please select the plan type.'
                }
            )

        if not premium:

            return render(
                request,
                'admin-add-insurance-plan.html',
                {
                    'user': request.user,
                    'error':
                        'Please enter the premium amount.'
                }
            )

        try:

            premium_value = float(premium)

            if premium_value <= 0:

                raise ValueError

        except (ValueError, TypeError):

            return render(
                request,
                'admin-add-insurance-plan.html',
                {
                    'user': request.user,
                    'error':
                        'Premium must be a valid amount greater than 0.'
                }
            )

        # ----------------------------------------------------
        # Insured Value
        # ----------------------------------------------------

        insured_value_final = None

        if insured_value:

            try:

                insured_value_final = float(
                    insured_value
                )

                if insured_value_final <= 0:
                    raise ValueError

            except (ValueError, TypeError):

                return render(
                    request,
                    'admin-add-insurance-plan.html',
                    {
                        'user': request.user,
                        'error':
                            'Insured value must be a valid amount greater than 0.'
                    }
                )

        # ----------------------------------------------------
        # Duration
        # ----------------------------------------------------

        if not duration_years:

            duration_years = 1

        try:

            duration_value = int(
                duration_years
            )

            if duration_value <= 0:

                raise ValueError

        except (ValueError, TypeError):

            return render(
                request,
                'admin-add-insurance-plan.html',
                {
                    'user': request.user,
                    'error':
                        'Duration must be a valid number of years.'
                }
            )

        # ----------------------------------------------------
        # Create Insurance Plan
        # ----------------------------------------------------

        InsurancePlan.objects.create(

            name=name,

            plan_type=plan_type,

            description=description
                if description else None,

            insured_value=insured_value_final,

            premium=premium_value,

            duration_years=duration_value,

            is_active=True
                if is_active == 'on'
                else False
        )

        return redirect(
            '/admin-insurance-plans/'
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        'admin-add-insurance-plan.html',
        {
            'user': request.user
        }
    )

def available_policies(request):

    if not request.user.is_authenticated:
        return redirect('/')

    # --------------------------------------------------------
    # Check whether the logged-in user already has a policy
    # --------------------------------------------------------

    if Policy.objects.filter(policyholder=request.user).exists():
        return redirect('/my-claims/')

    # --------------------------------------------------------
    # Get active insurance plans
    # --------------------------------------------------------

    plans = InsurancePlan.objects.filter(
        is_active=True
    ).order_by('premium')

    return render(
        request,
        'available-policies.html',
        {
            'user': request.user,
            'plans': plans,
        }
    )

def register_policy(request, plan_id):

    if not request.user.is_authenticated:
        return redirect('/')

    # --------------------------------------------------------
    # Prevent multiple policies for the same user
    # --------------------------------------------------------

    if Policy.objects.filter(
        policyholder=request.user
    ).exists():
        return redirect('/my-claims/')

    plan = get_object_or_404(
        InsurancePlan,
        id=plan_id,
        is_active=True
    )

    if request.method == 'POST':

        # ----------------------------------------------------
        # Policyholder Details
        # ----------------------------------------------------

        full_name = request.POST.get(
            'full_name',
            ''
        ).strip()

        phone_number = request.POST.get(
            'phone_number',
            ''
        ).strip()

        address = request.POST.get(
            'address',
            ''
        ).strip()

        # ----------------------------------------------------
        # Vehicle Details
        # ----------------------------------------------------

        vehicle_make = request.POST.get(
            'vehicle_make',
            ''
        ).strip()

        vehicle_model = request.POST.get(
            'vehicle_model',
            ''
        ).strip()

        vehicle_variant = request.POST.get(
            'vehicle_variant',
            ''
        ).strip()

        vehicle_year = request.POST.get(
            'vehicle_year'
        )

        current_year = date.today().year

        try:

            vehicle_year_int = int(
                vehicle_year
            )

        except (
            ValueError,
            TypeError
        ):

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter a valid vehicle year.'
                }
            )

        if (
            vehicle_year_int < 2000
            or vehicle_year_int > current_year
        ):

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        f'Vehicle year must be between 2000 and {current_year}.'
                }
            )

        registration_number = request.POST.get(
            'registration_number',
            ''
        ).strip().upper()

        # ----------------------------------------------------
        # Registration Number Validation
        # ----------------------------------------------------

        registration_pattern = (
            r'^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{4}$'
        )

        if not re.fullmatch(
            registration_pattern,
            registration_number
        ):

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter a valid vehicle registration number, '
                        'for example MH01AB1234.'
                }
            )

        fuel_type = request.POST.get(
            'fuel_type'
        )

        # ----------------------------------------------------
        # Fuel Type Validation
        # ----------------------------------------------------

        valid_fuel_types = [
            'Petrol',
            'Diesel',
            'CNG',
            'Electric',
            'Hybrid',
            'Other'
        ]

        if fuel_type not in valid_fuel_types:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please select a valid fuel type.'
                }
            )

        if (
            fuel_type == 'Electric'
            and vehicle_year_int < 2013
        ):

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Electric vehicles are not allowed for vehicle years before 2013.'
                }
            )

        if (
            fuel_type == 'Hybrid'
            and vehicle_year_int < 2015
        ):

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Hybrid vehicles are not allowed for vehicle years before 2015.'
                }
            )

        # ----------------------------------------------------
        # Previous Insurance
        # ----------------------------------------------------

        has_previous_insurance = request.POST.get(
            'has_previous_insurance',
            ''
        ).strip()

        previous_insurer = ''
        previous_policy_number = ''
        previous_policy_expiry = None
        no_claim_bonus = ''

        if has_previous_insurance == 'yes':

            previous_insurer = request.POST.get(
                'previous_insurer',
                ''
            ).strip()

            previous_policy_number = request.POST.get(
                'previous_policy_number',
                ''
            ).strip()

            previous_policy_expiry = request.POST.get(
                'previous_policy_expiry'
            )

            no_claim_bonus = request.POST.get(
                'no_claim_bonus',
                ''
            ).strip()

        # ----------------------------------------------------
        # Nominee Details
        # ----------------------------------------------------

        nominee_name = request.POST.get(
            'nominee_name',
            ''
        ).strip()

        nominee_relationship = request.POST.get(
            'nominee_relationship'
        )

        nominee_date_of_birth = request.POST.get(
            'nominee_date_of_birth'
        )

        nominee_date_of_birth_obj = None

        if nominee_date_of_birth:

            try:

                nominee_date_of_birth_obj = (
                    timezone.datetime.strptime(
                        nominee_date_of_birth,
                        '%Y-%m-%d'
                    ).date()
                )

            except ValueError:

                return render(
                    request,
                    'register-policy.html',
                    {
                        'user': request.user,
                        'plan': plan,
                        'error':
                            'Please enter a valid nominee date of birth.'
                    }
                )

            today = date.today()

            # ------------------------------------------------
            # Nominee cannot be born in the future
            # ------------------------------------------------

            if nominee_date_of_birth_obj > today:

                return render(
                    request,
                    'register-policy.html',
                    {
                        'user': request.user,
                        'plan': plan,
                        'error':
                            'Nominee date of birth cannot be in the future.'
                    }
                )

            # ------------------------------------------------
            # Nominee cannot be more than 100 years old
            # ------------------------------------------------

            minimum_dob = date(
                today.year - 100,
                today.month,
                today.day
            )

            if nominee_date_of_birth_obj < minimum_dob:

                return render(
                    request,
                    'register-policy.html',
                    {
                        'user': request.user,
                        'plan': plan,
                        'error':
                            'Nominee date of birth cannot be more than 100 years ago.'
                    }
                )

        # ----------------------------------------------------
        # Declaration
        # ----------------------------------------------------

        declaration_accepted = request.POST.get(
            'declaration'
        )

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if not full_name:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter your full name.'
                }
            )

        # ----------------------------------------------------
        # Phone Number Validation
        # ----------------------------------------------------

        if not phone_number:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter your phone number.'
                }
            )

        if not phone_number.isdigit() or len(phone_number) != 10:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Phone number must contain exactly 10 digits.'
                }
            )

        # ----------------------------------------------------
        # Address Validation
        # ----------------------------------------------------

        if not address:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter your address.'
                }
            )

        # ----------------------------------------------------
        # Vehicle Validation
        # ----------------------------------------------------

        if not vehicle_make or not vehicle_model:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter your vehicle make and model.'
                }
            )

        if not registration_number:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter your vehicle registration number.'
                }
            )

        # ----------------------------------------------------
        # Previous Insurance Validation
        # ----------------------------------------------------

        if has_previous_insurance not in ['yes', 'no']:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please select whether you have previous insurance.'
                }
            )

        if has_previous_insurance == 'yes':

            if not previous_insurer:

                return render(
                    request,
                    'register-policy.html',
                    {
                        'user': request.user,
                        'plan': plan,
                        'error':
                            'Please enter your previous insurer.'
                    }
                )

            if not previous_policy_number:

                return render(
                    request,
                    'register-policy.html',
                    {
                        'user': request.user,
                        'plan': plan,
                        'error':
                            'Please enter your previous policy number.'
                    }
                )

        # ----------------------------------------------------
        # Nominee Validation
        # ----------------------------------------------------

        if not nominee_name or not nominee_relationship:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please enter the nominee details.'
                }
            )

        # ----------------------------------------------------
        # Declaration Validation
        # ----------------------------------------------------

        if declaration_accepted != 'on':

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'Please accept the declaration before '
                        'registering the policy.'
                }
            )

        # ----------------------------------------------------
        # Check Duplicate Vehicle Registration
        # ----------------------------------------------------

        existing_policy = Policy.objects.filter(
            registration_number__iexact=registration_number
        ).exists()

        if existing_policy:

            return render(
                request,
                'register-policy.html',
                {
                    'user': request.user,
                    'plan': plan,
                    'error':
                        'This vehicle registration number is already registered.'
                }
            )

        # ----------------------------------------------------
        # Generate Policy Number
        # ----------------------------------------------------

        last_policy = Policy.objects.order_by(
            '-id'
        ).first()

        if last_policy:

            policy_number = (
                f"POL{last_policy.id + 1:05d}"
            )

        else:

            policy_number = "POL00001"

        # ----------------------------------------------------
        # Policy Dates
        # ----------------------------------------------------

        start_date = date.today()

        end_date = start_date + relativedelta(
            years=plan.duration_years
        )

        # ----------------------------------------------------
        # Create Policy
        # ----------------------------------------------------

        Policy.objects.create(

            policyholder=request.user,

            insurance_plan=plan,

            policy_number=policy_number,

            full_name=full_name,

            phone_number=phone_number,

            address=address,

            vehicle_make=vehicle_make,

            vehicle_model=vehicle_model,

            vehicle_variant=vehicle_variant
                if vehicle_variant else None,

            vehicle_year=vehicle_year_int,

            registration_number=registration_number,

            fuel_type=fuel_type
                if fuel_type else None,

            coverage_type=plan.plan_type,

            insured_value=plan.insured_value,

            start_date=start_date,

            end_date=end_date,

            status='active',

            # Previous insurance
            previous_insurer=previous_insurer
                if has_previous_insurance == 'yes'
                and previous_insurer else None,

            previous_policy_number=previous_policy_number
                if has_previous_insurance == 'yes'
                and previous_policy_number else None,

            previous_policy_expiry=previous_policy_expiry
                if has_previous_insurance == 'yes'
                and previous_policy_expiry else None,

            no_claim_bonus=no_claim_bonus
                if has_previous_insurance == 'yes'
                and no_claim_bonus else None,

            # Nominee
            nominee_name=nominee_name,

            nominee_relationship=nominee_relationship,

            nominee_date_of_birth=
                nominee_date_of_birth_obj
                if nominee_date_of_birth_obj
                else None,

            declaration_accepted=True
        )

        return redirect('/my-claims/')

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render(
        request,
        'register-policy.html',
        {
            'user': request.user,
            'plan': plan
        }
    )

def admin_add_officer(request):

    if not request.user.is_authenticated:
        return redirect('/')

    if not is_admin(request):
        return redirect('/dashboard/')

    if request.method == 'POST':

        first_name = request.POST.get(
            'first_name',
            ''
        ).strip()

        last_name = request.POST.get(
            'last_name',
            ''
        ).strip()

        email = request.POST.get(
            'email',
            ''
        ).strip()

        password = request.POST.get(
            'password',
            ''
        )

        confirm_password = request.POST.get(
            'confirm_password',
            ''
        )

        if password != confirm_password:

            return render(
                request,
                'admin-add-officer.html',
                {
                    'user': request.user,
                    'error': 'Passwords do not match.'
                }
            )

        if User.objects.filter(
            username=email
        ).exists():

            return render(
                request,
                'admin-add-officer.html',
                {
                    'user': request.user,
                    'error': 'An account with this email already exists.'
                }
            )

        officer = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        UserProfile.objects.create(
            user=officer,
            role='officer'
        )

        return redirect('/admin-officers/')

    return render(
        request,
        'admin-add-officer.html',
        {
            'user': request.user
        }
    )