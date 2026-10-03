from django.test import TestCase
from claims.ml.predict import predict_claim_risk

class MLModelTestCase(TestCase):
    def test_prediction_output(self):
        risk, confidence, low, med, high = predict_claim_risk(
            accident_type='collision',
            driver_age=30,
            previous_claims=0,
            days_to_report=2,
            police_report_status='reported',
            driver_authorised=True,
            third_party_involved=False,
            third_party_injury=False,
            third_party_damage=False,
            estimated_damage=15000,
            claim_amount=12000,
            insured_value=300000
        )
        self.assertIn(risk, ['low', 'medium', 'high'])
        self.assertGreaterEqual(confidence, 0.0)