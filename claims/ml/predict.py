import os
import joblib
import numpy as np
import pandas as pd
import shap
from django.utils import timezone


# ============================================================
# LOAD TRAINED MODEL
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    'claim_risk_model.pkl'
)

model = joblib.load(MODEL_PATH)


# ============================================================
# CREATE CLAIM DATA
# ============================================================

def create_claim_data(
    accident_type,
    driver_age,
    previous_claims,
    days_to_report,
    police_report_status,
    driver_authorised,
    third_party_involved,
    third_party_injury,
    third_party_damage,
    estimated_damage,
    claim_amount,
    claim_to_damage_ratio,
    claim_to_insured_value_ratio
):

    return pd.DataFrame([
        {
            'accident_type': accident_type,

            'driver_age': driver_age,

            'previous_claims': previous_claims,

            'days_to_report': days_to_report,

            'police_report_status': police_report_status,

            'driver_authorised': int(
                bool(driver_authorised)
            ),

            'third_party_involved': int(
                bool(third_party_involved)
            ),

            'third_party_injury': int(
                bool(third_party_injury)
            ),

            'third_party_damage': int(
                bool(third_party_damage)
            ),

            'estimated_damage': estimated_damage,

            'claim_amount': claim_amount,

            'claim_to_damage_ratio': claim_to_damage_ratio,

            'claim_to_insured_value_ratio':
                claim_to_insured_value_ratio
        }
    ])

# ============================================================
# CALCULATE DERIVED FEATURES
# ============================================================

def calculate_claim_ratios(
    estimated_damage,
    claim_amount,
    insured_value
):

    # --------------------------------------------------------
    # Claim amount / estimated damage
    # --------------------------------------------------------

    if (
        estimated_damage is not None
        and float(estimated_damage) > 0
    ):

        claim_to_damage_ratio = (
            float(claim_amount)
            / float(estimated_damage)
        )

    else:

        claim_to_damage_ratio = 0.55


    # --------------------------------------------------------
    # Claim amount / insured value
    # --------------------------------------------------------

    if (
        insured_value is not None
        and float(insured_value) > 0
    ):

        claim_to_insured_value_ratio = (
            float(claim_amount)
            / float(insured_value)
        )

    else:

        claim_to_insured_value_ratio = 0.005


    # --------------------------------------------------------
    # Keep within the training-data range
    # --------------------------------------------------------

    claim_to_damage_ratio = min(
        max(claim_to_damage_ratio, 0.55),
        1.22
    )

    claim_to_insured_value_ratio = min(
        max(claim_to_insured_value_ratio, 0.005),
        1.254
    )


    return (
        round(claim_to_damage_ratio, 3),
        round(claim_to_insured_value_ratio, 4)
    )
# ============================================================
# PREDICT CLAIM RISK AND CONFIDENCE
# ============================================================

def predict_claim_risk(
    accident_type,
    driver_age,
    previous_claims,
    days_to_report,
    police_report_status,
    driver_authorised,
    third_party_involved,
    third_party_injury,
    third_party_damage,
    estimated_damage,
    claim_amount,
    insured_value
):

    # --------------------------------------------------------
    # Calculate derived ML features
    # --------------------------------------------------------

    (
        claim_to_damage_ratio,
        claim_to_insured_value_ratio
    ) = calculate_claim_ratios(
        estimated_damage,
        claim_amount,
        insured_value
    )


    # --------------------------------------------------------
    # Create model input
    # --------------------------------------------------------

    data = create_claim_data(
        accident_type=accident_type,
        driver_age=driver_age,
        previous_claims=previous_claims,
        days_to_report=days_to_report,
        police_report_status=police_report_status,
        driver_authorised=driver_authorised,
        third_party_involved=third_party_involved,
        third_party_injury=third_party_injury,
        third_party_damage=third_party_damage,
        estimated_damage=estimated_damage,
        claim_amount=claim_amount,
        claim_to_damage_ratio=claim_to_damage_ratio,
        claim_to_insured_value_ratio=
            claim_to_insured_value_ratio
    )


    # --------------------------------------------------------
    # Get predicted risk
    # --------------------------------------------------------

    prediction = model.predict(
        data
    )[0]


    # --------------------------------------------------------
    # Get probability for each risk class
    # --------------------------------------------------------

    probabilities = model.predict_proba(
        data
    )[0]


    class_probabilities = dict(
        zip(
            model.classes_,
            probabilities
        )
    )


    # --------------------------------------------------------
    # Get confidence
    # --------------------------------------------------------

    confidence = (
        class_probabilities[prediction]
        * 100
    )


    # --------------------------------------------------------
    # Get individual risk probabilities
    # --------------------------------------------------------

    low_probability = (
        class_probabilities.get(
            'low',
            0
        ) * 100
    )

    medium_probability = (
        class_probabilities.get(
            'medium',
            0
        ) * 100
    )

    high_probability = (
        class_probabilities.get(
            'high',
            0
        ) * 100
    )


    return (
        prediction,
        round(confidence, 2),
        round(low_probability, 2),
        round(medium_probability, 2),
        round(high_probability, 2)
    )

# ============================================================
# SHAP EXPLAINER
# ============================================================

_shap_explainer = None


def get_shap_explainer():

    global _shap_explainer

    if _shap_explainer is None:

        # ----------------------------------------------------
        # Load a small representative background sample from
        # the same final dataset used to train the model.
        # ----------------------------------------------------

        dataset_path = os.path.join(
            BASE_DIR,
            'claim_training_data_final.csv'
        )

        background_data = pd.read_csv(
            dataset_path
        )

        # Remove target column.
        if 'risk_level' in background_data.columns:

            background_data = background_data.drop(
                columns=['risk_level']
            )

        # Use a small sample to keep SHAP reasonably fast.
        background_data = background_data.sample(
            n=min(50, len(background_data)),
            random_state=42
        )

        # ----------------------------------------------------
        # Use the SAME preprocessor as the trained model.
        # ----------------------------------------------------

        preprocessor = model.named_steps[
            'preprocessor'
        ]

        background_transformed = (
            preprocessor.transform(
                background_data
            )
        )

        # Convert sparse matrix to dense.
        if hasattr(
            background_transformed,
            'toarray'
        ):

            background_transformed = (
                background_transformed.toarray()
            )

        # ----------------------------------------------------
        # The classifier is the final Gradient Boosting model.
        # ----------------------------------------------------

        classifier = model.named_steps[
            'classifier'
        ]

        def predict_proba_function(data):

            return classifier.predict_proba(
                data
            )

        # ----------------------------------------------------
        # Multiclass-compatible permutation SHAP.
        # ----------------------------------------------------

        _shap_explainer = shap.PermutationExplainer(
            predict_proba_function,
            background_transformed
        )

    return _shap_explainer

# ============================================================
# MAP TRANSFORMED FEATURES
# BACK TO ORIGINAL MODEL FEATURES
# ============================================================

def get_feature_groups():

    preprocessor = model.named_steps[
        'preprocessor'
    ]

    feature_names = (
        preprocessor.get_feature_names_out()
    )

    original_features = [

        'accident_type',

        'police_report_status',

        'driver_age',

        'previous_claims',

        'days_to_report',

        'driver_authorised',

        'third_party_involved',

        'third_party_injury',

        'third_party_damage',

        'estimated_damage',

        'claim_amount',

        'claim_to_damage_ratio',

        'claim_to_insured_value_ratio'
    ]

    feature_groups = []

    for feature_name in feature_names:

        clean_name = str(feature_name)

        # ----------------------------------------------------
        # Remove ColumnTransformer prefixes
        # ----------------------------------------------------

        for prefix in (
            'categorical__',
            'numerical__',
            'remainder__'
        ):

            if clean_name.startswith(prefix):

                clean_name = clean_name[
                    len(prefix):
                ]

                break

        # ----------------------------------------------------
        # Match transformed feature to original feature
        # ----------------------------------------------------

        matched_feature = None

        for original_feature in original_features:

            if (
                clean_name == original_feature
                or clean_name.startswith(
                    original_feature + '_'
                )
            ):

                matched_feature = original_feature
                break

        if matched_feature is None:
            matched_feature = clean_name

        feature_groups.append(
            matched_feature
        )

    return (
        feature_names,
        feature_groups
    )

# ============================================================
# EXTRACT SHAP VALUES
# ============================================================

def get_predicted_class_shap_values(
    shap_values,
    class_index,
    number_of_features,
    number_of_classes
):

    # --------------------------------------------------------
    # Convert SHAP result to numpy array
    # --------------------------------------------------------

    if hasattr(shap_values, 'values'):

        values = np.asarray(
            shap_values.values
        )

    else:

        values = np.asarray(
            shap_values
        )


    # --------------------------------------------------------
    # Debug information
    # --------------------------------------------------------

    print(
        "SHAP values shape:",
        values.shape
    )


    # ========================================================
    # Expected multiclass PermutationExplainer output
    #
    # samples x features x classes
    # ========================================================

    if values.ndim == 3:

        if (
            values.shape[0] == 1
            and values.shape[1] == number_of_features
            and values.shape[2] == number_of_classes
        ):

            return values[
                0,
                :,
                class_index
            ]


        # ----------------------------------------------------
        # samples x classes x features
        # ----------------------------------------------------

        if (
            values.shape[0] == 1
            and values.shape[1] == number_of_classes
            and values.shape[2] == number_of_features
        ):

            return values[
                0,
                class_index,
                :
            ]


        # ----------------------------------------------------
        # classes x samples x features
        # ----------------------------------------------------

        if (
            values.shape[0] == number_of_classes
            and values.shape[1] == 1
            and values.shape[2] == number_of_features
        ):

            return values[
                class_index,
                0,
                :
            ]


    # ========================================================
    # Single-output SHAP
    # ========================================================

    if values.ndim == 2:

        if (
            values.shape[0] == 1
            and values.shape[1] == number_of_features
        ):

            return values[0]


    # ========================================================
    # Some SHAP versions return:
    #
    # samples x features
    #
    # for one selected output
    # ========================================================

    if values.ndim == 2:

        if values.shape == (
            number_of_features,
            number_of_classes
        ):

            return values[
                :,
                class_index
            ]


        if values.shape == (
            number_of_classes,
            number_of_features
        ):

            return values[
                class_index,
                :
            ]


    raise ValueError(
        'Unsupported SHAP output shape: '
        f'{values.shape}'
    )

# ============================================================
# FORMAT FEATURE VALUE
# ============================================================

# ============================================================
# FORMAT FEATURE VALUE
# ============================================================

def format_feature_value(
    feature,
    claim
):

    # --------------------------------------------------------
    # Claim-to-damage ratio
    # --------------------------------------------------------

    if feature == 'claim_to_damage_ratio':

        try:

            estimated_damage = float(
                claim.estimated_damage
            )

            claim_amount = float(
                claim.claim_amount
            )

            if estimated_damage > 0:

                ratio = (
                    claim_amount
                    / estimated_damage
                )

                return f'{ratio:.2f}'

        except (
            AttributeError,
            TypeError,
            ValueError
        ):

            pass

        return 'Not available'


    # --------------------------------------------------------
    # Claim-to-insured-value ratio
    # --------------------------------------------------------

    if feature == 'claim_to_insured_value_ratio':

        try:

            insured_value = (
                claim.policy.insured_value
            )

            claim_amount = float(
                claim.claim_amount
            )

            if (
                insured_value is not None
                and float(insured_value) > 0
            ):

                ratio = (
                    claim_amount
                    / float(insured_value)
                )

                return f'{ratio:.3f}'

        except (
            AttributeError,
            TypeError,
            ValueError
        ):

            pass

        return 'Not available'


    # --------------------------------------------------------
    # Normal Claim fields
    # --------------------------------------------------------

    value = getattr(
        claim,
        feature,
        None
    )


    if value is None:

        return 'Not available'

    value = getattr(
        claim,
        feature,
        None
    )


    if value is None:

        return 'Not available'


    # --------------------------------------------------------
    # Driver age
    # --------------------------------------------------------

    if feature == 'driver_age':

        try:

            return (
                f'{int(value)} years old'
            )

        except (
            ValueError,
            TypeError
        ):

            return str(value)


    # --------------------------------------------------------
    # Previous claims
    # --------------------------------------------------------

    if feature == 'previous_claims':

        try:

            return (
                f'{int(value)} previous claims'
            )

        except (
            ValueError,
            TypeError
        ):

            return str(value)


    # --------------------------------------------------------
    # Reporting delay
    # --------------------------------------------------------

    if feature == 'days_to_report':

        try:

            days = int(value)

            if days == 1:

                return (
                    '1 day after the incident'
                )

            return (
                f'{days} days after the incident'
            )

        except (
            ValueError,
            TypeError
        ):

            return str(value)


    # --------------------------------------------------------
    # Money
    # --------------------------------------------------------

    if feature in (
        'estimated_damage',
        'claim_amount'
    ):

        try:

            return (
                f'₹{float(value):,.2f}'
            )

        except (
            ValueError,
            TypeError
        ):

            return str(value)


    # --------------------------------------------------------
    # Boolean fields
    # --------------------------------------------------------

    if feature in (
        'driver_authorised',
        'third_party_involved',
        'third_party_injury',
        'third_party_damage'
    ):

        return (
            'Yes'
            if bool(value)
            else 'No'
        )


    # --------------------------------------------------------
    # Police report
    # --------------------------------------------------------

    if feature == 'police_report_status':

        value_text = (
            str(value)
            .strip()
            .lower()
        )


        if value_text == 'reported':

            return 'Reported'


        if value_text == 'not_reported':

            return 'Not reported'


        if value_text == 'not_required':

            return 'Not required'


        return str(value)


    # --------------------------------------------------------
    # Vehicle year
    # --------------------------------------------------------

    if feature == 'vehicle_year':

        try:

            year = int(value)

            current_year = (
                timezone.localdate().year
            )

            age = current_year - year


            if age >= 0:

                return (
                    f'{year} '
                    f'({age} years old)'
                )


            return str(year)

        except (
            ValueError,
            TypeError
        ):

            return str(value)


    # --------------------------------------------------------
    # Ratios
    # --------------------------------------------------------

    if feature == 'claim_to_damage_ratio':

        try:

            return (
                f'{float(value):.2f}'
            )

        except (
            ValueError,
            TypeError
        ):

            return str(value)


    if feature == 'claim_to_insured_value_ratio':

        try:

            return (
                f'{float(value):.3f}'
            )

        except (
            ValueError,
            TypeError
        ):

            return str(value)


    return str(value)


# ============================================================
# CREATE PRACTICAL OFFICER ACTION
# ============================================================

def create_officer_action(
    feature,
    claim
):

    value = getattr(
        claim,
        feature,
        None
    )


    # --------------------------------------------------------
    # Reporting delay
    # --------------------------------------------------------

    if feature == 'days_to_report':

        try:

            days = int(value)

            return (
                f'The claim was reported '
                f'{days} days after the incident. '
                'Verify the reason for the delay '
                'and the supporting documents.'
            )

        except (
            ValueError,
            TypeError
        ):

            return (
                'Verify the incident date and '
                'claim reporting information.'
            )


    # --------------------------------------------------------
    # Previous claims
    # --------------------------------------------------------

    if feature == 'previous_claims':
        try:
            count = int(value)

            if count == 1:

                claim_text = (
                '1 previous claim is recorded.'
            )

            else:

                claim_text = (
                f'{count} previous claims are recorded.'
            )

            return (
            f'{claim_text} '
            'Review the claim history for consistency.'
        )
        except (
        ValueError,
        TypeError
    ):
            return (
            'Verify the policyholder claim history.'
        )


    # --------------------------------------------------------
    # Driver age
    # --------------------------------------------------------

    if feature == 'driver_age':

        try:

            age = int(value)

            return (
                f'The driver is {age} years old. '
                'Verify the driving licence and confirm '
                'eligibility under the policy.'
            )

        except (
            ValueError,
            TypeError
        ):

            return (
                'Verify the driver details and '
                'licence information.'
            )


    # --------------------------------------------------------
    # Police report
    # --------------------------------------------------------

    if feature == 'police_report_status':

        status = (
            str(value)
            .strip()
            .lower()
        )


        if status == 'not_reported':

            return (
                'No police report has been indicated. '
                'Check whether a police report is required '
                'for this incident and verify the reason '
                'and supporting documents.'
            )


        if status == 'reported':

            return (
                'A police report has been indicated. '
                'Verify that the report supports the '
                'incident details.'
            )


        return (
            'A police report is marked as not required. '
            'Verify that this is appropriate for the incident.'
        )


    # --------------------------------------------------------
    # Accident type
    # --------------------------------------------------------

    if feature == 'accident_type':

        accident = (
            str(value)
            .strip()
            .lower()
        )


        if accident == 'fire':

            return (
                'The incident involves fire damage. '
                'Verify the cause of the fire and review '
                'the supporting evidence.'
            )


        if accident == 'theft':

            return (
                'The incident involves theft. '
                'Verify the police report, vehicle ownership '
                'and supporting documents.'
            )


        if accident == 'collision':

            return (
                'The incident involves a collision. '
                'Verify the accident details, vehicle damage '
                'and repair estimate.'
            )


        if accident in (
            'natural disaster',
            'flood',
            'storm'
        ):

            return (
                'The incident is related to a natural event. '
                'Verify the incident circumstances, date, '
                'location and supporting evidence.'
            )


        return (
            f'The incident type is recorded as {value}. '
            'Verify the incident details and supporting evidence.'
        )


    # --------------------------------------------------------
    # Driver authorised
    # --------------------------------------------------------

    if feature == 'driver_authorised':

        if bool(value):

            return (
                'The driver is marked as authorised under '
                'the policy. Verify the licence and policy details.'
            )

        return (
            'The driver is marked as not authorised under '
            'the policy. Verify the policy terms and driver details.'
        )


    # --------------------------------------------------------
    # Third party
    # --------------------------------------------------------

    if feature == 'third_party_involved':

        if bool(value):

            return (
                'A third party is involved. Verify the '
                'third-party details and supporting evidence.'
            )

        return (
            'No third party is recorded. Verify the '
            'incident description and submitted documents.'
        )


    # --------------------------------------------------------
    # Third-party injury
    # --------------------------------------------------------

    if feature == 'third_party_injury':

        if bool(value):

            return (
                'Third-party injury is indicated. Verify '
                'the incident details and supporting documentation.'
            )

        return (
            'No third-party injury is indicated.'
        )


    # --------------------------------------------------------
    # Third-party damage
    # --------------------------------------------------------

    if feature == 'third_party_damage':

        if bool(value):

            return (
                'Third-party property or vehicle damage is '
                'indicated. Verify the damage information.'
            )

        return (
            'No third-party damage is indicated.'
        )


    # --------------------------------------------------------
    # Claim amount
    # --------------------------------------------------------

    if feature == 'claim_amount':

        claim_amount = format_feature_value(
            'claim_amount',
            claim
        )


        estimated_damage = getattr(
            claim,
            'estimated_damage',
            None
        )


        if estimated_damage is not None:

            estimated_damage_text = (
                format_feature_value(
                    'estimated_damage',
                    claim
                )
            )


            return (
                f'The requested claim amount is '
                f'{claim_amount}, compared with estimated '
                f'damage of {estimated_damage_text}. '
                'Verify the damage assessment and repair documents.'
            )


        return (
            f'The requested claim amount is '
            f'{claim_amount}. Verify the damage assessment '
            'and supporting documents.'
        )


    # --------------------------------------------------------
    # Estimated damage
    # --------------------------------------------------------

    if feature == 'estimated_damage':

        damage = format_feature_value(
            'estimated_damage',
            claim
        )


        return (
            f'The estimated damage is {damage}. '
            'Verify the damage assessment and repair documents.'
        )


    # --------------------------------------------------------
    # Claim to damage ratio
    # --------------------------------------------------------

    if feature == 'claim_to_damage_ratio':

        estimated_damage = getattr(
            claim,
            'estimated_damage',
            None
        )

        claim_amount = getattr(
            claim,
            'claim_amount',
            None
        )


        if (
            estimated_damage
            and float(estimated_damage) > 0
        ):

            ratio = (
                float(claim_amount)
                / float(estimated_damage)
            )


            return (
                f'The claim amount is approximately '
                f'{ratio:.2f} times the estimated damage. '
                'Verify the claimed amount against the '
                'damage assessment and repair estimate.'
            )


        return (
            'Verify the claim amount and estimated damage.'
        )


    # --------------------------------------------------------
    # Claim to insured value ratio
    # --------------------------------------------------------

    if feature == 'claim_to_insured_value_ratio':

        try:

            insured_value = (
                claim.policy.insured_value
            )

            claim_amount = float(
                claim.claim_amount
            )


            if (
                insured_value
                and float(insured_value) > 0
            ):

                ratio = (
                    claim_amount
                    / float(insured_value)
                )


                return (
                    f'The claim amount represents approximately '
                    f'{ratio:.1%} of the insured value. '
                    'Verify the claim amount against the policy '
                    'coverage and damage assessment.'
                )

        except (
            AttributeError,
            TypeError,
            ValueError
        ):

            pass


        return (
            'Verify the claim amount against the policy '
            'insured value.'
        )


    # --------------------------------------------------------
    # Default
    # --------------------------------------------------------

    return (
        f'{feature.replace("_", " ").title()} '
        f'is recorded as {value}. Verify the information '
        'against the submitted claim documents.'
    )


# ============================================================
# GENERATE SHAP-BASED OFFICER EXPLANATION
# ============================================================

def generate_claim_explanation(
    claim
):

    try:

        # ----------------------------------------------------
        # Get insured value from policy
        # ----------------------------------------------------

        insured_value = (
            claim.policy.insured_value
        )


        # ----------------------------------------------------
        # Calculate derived features
        # ----------------------------------------------------

        (
            claim_to_damage_ratio,
            claim_to_insured_value_ratio
        ) = calculate_claim_ratios(
            claim.estimated_damage,
            claim.claim_amount,
            insured_value
        )


        # ----------------------------------------------------
        # Create model input
        # ----------------------------------------------------

        data = create_claim_data(

            accident_type=
                claim.accident_type,

            driver_age=
                claim.driver_age,

            previous_claims=
                claim.previous_claims,

            days_to_report=
                claim.days_to_report,

            police_report_status=
                claim.police_report_status,

            driver_authorised=
                claim.driver_authorised,

            third_party_involved=
                claim.third_party_involved,

            third_party_injury=
                claim.third_party_injury,

            third_party_damage=
                claim.third_party_damage,

            estimated_damage=
                claim.estimated_damage,

            claim_amount=
                claim.claim_amount,

            claim_to_damage_ratio=
                claim_to_damage_ratio,

            claim_to_insured_value_ratio=
                claim_to_insured_value_ratio
        )


        # ----------------------------------------------------
        # Get prediction
        # ----------------------------------------------------

        prediction = model.predict(
            data
        )[0]


        classes = list(
            model.classes_
        )


        class_index = classes.index(
            prediction
        )


        # ----------------------------------------------------
        # Transform using the SAME preprocessor
        # ----------------------------------------------------

        preprocessor = model.named_steps[
            'preprocessor'
        ]


        transformed_data = (
            preprocessor.transform(
                data
            )
        )


        # Convert sparse matrix to dense matrix.
        if hasattr(
            transformed_data,
            'toarray'
        ):

            transformed_data = (
                transformed_data.toarray()
            )


        # ----------------------------------------------------
        # SHAP
        # ----------------------------------------------------

        explainer = get_shap_explainer()
        shap_result = explainer(transformed_data)


        # ----------------------------------------------------
        # Feature names and groups
        # ----------------------------------------------------

        (
            feature_names,
            feature_groups
        ) = get_feature_groups()


        predicted_class_values = (
            get_predicted_class_shap_values(

                shap_result,

                class_index,

                len(feature_names),

                len(classes)
            )
        )


        # ----------------------------------------------------
        # Combine one-hot features
        # ----------------------------------------------------

        grouped_contributions = {}


        for index, feature_group in enumerate(
            feature_groups
        ):

            contribution = float(
                predicted_class_values[index]
            )


            if feature_group not in (
                grouped_contributions
            ):

                grouped_contributions[
                    feature_group
                ] = 0.0


            grouped_contributions[
                feature_group
            ] += contribution


        # ----------------------------------------------------
        # Sort by SHAP influence
        # ----------------------------------------------------

        sorted_features = sorted(

            grouped_contributions.items(),

            key=lambda item:
                abs(item[1]),

            reverse=True
        )


        # Remove zero-influence features.
        sorted_features = [

            item

            for item in sorted_features

            if abs(item[1]) > 0.000001
        ]


        # ----------------------------------------------------
        # Select top 4 factors
        # ----------------------------------------------------

        selected_features = (
            sorted_features[:4]
        )


        # ----------------------------------------------------
        # No useful SHAP factor
        # ----------------------------------------------------

        if not selected_features:

            return [{
                'score': 1,

                'title':
                    'AI assessment',

                'message':
                    (
                        'The AI model has generated a risk '
                        'prediction, but no individual input '
                        'had a significant feature-level '
                        'influence for this claim. Complete '
                        'the normal claim verification process.'
                    )
            }]


        # ----------------------------------------------------
        # Build explanations
        # ----------------------------------------------------

        explanations = []


        maximum_influence = max(
            abs(contribution)

            for _, contribution
            in selected_features
        )


        risk_label = str(
            prediction
        ).title()


        titles = {

            'days_to_report':
                'Reporting information',

            'previous_claims':
                'Previous claim history',

            'driver_age':
                'Driver information',

            'police_report_status':
                'Police report',

            'accident_type':
                'Incident type',

            'driver_authorised':
                'Driver authorisation',

            'third_party_involved':
                'Third-party involvement',

            'third_party_injury':
                'Third-party injury',

            'third_party_damage':
                'Third-party damage',

            'estimated_damage':
                'Estimated damage',

            'claim_amount':
                'Claim amount',

            'claim_to_damage_ratio':
                'Claim-to-damage ratio',

            'claim_to_insured_value_ratio':
                'Claim-to-insured-value ratio'
        }


        for feature, contribution in (
            selected_features
        ):

            absolute_influence = abs(
                contribution
            )


            # Determine influence strength.
            if (
                maximum_influence > 0
                and absolute_influence
                >= maximum_influence * 0.70
            ):

                strength = 'Strong'


            elif (
                maximum_influence > 0
                and absolute_influence
                >= maximum_influence * 0.35
            ):

                strength = 'Moderate'


            else:

                strength = 'Lower'


            # Determine direction.
            if contribution > 0:

                direction = (
                    f'{strength} influence toward '
                    f'{risk_label} Risk.'
                )

            else:

                direction = (
                    f'{strength} influence away from '
                    f'{risk_label} Risk.'
                )


            # Practical officer action.
            action = create_officer_action(
                feature,
                claim
            )


            title = titles.get(
                feature,
                feature.replace(
                    '_',
                    ' '
                ).title()
            )


            message = (
                f'{direction} '
                f'{action}'
            )


            explanations.append({

                'score':
                    round(
                        absolute_influence,
                        6
                    ),

                'title':
                    title,

                'message':
                    message
            })


        return explanations


    except Exception as error:

        # Do not stop the officer review page if
        # SHAP itself encounters an issue.

        print(
            'SHAP explanation error:',
            error
        )


        return [{

            'score':
                1,

            'title':
                'AI explanation unavailable',

            'message':
                (
                    'The AI risk prediction is available, '
                    'but a feature-level explanation could '
                    'not be generated for this claim. '
                    'Complete the normal claim review and '
                    'document verification process.'
                )
        }]