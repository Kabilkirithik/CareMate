"""
Basic tests for CareMate tools
"""

import pytest
import json
from caremate.tools.patient_intelligence_tools import (
    PatientRecordRetrievalTool,
    IntentClassificationTool,
    DistressDetectionTool
)
from caremate.tools.orchestrator_tools import (
    PolicyEvaluationTool,
    ResponseGenerationTool
)


class TestPatientIntelligenceTools:
    """Tests for Patient Intelligence Agent tools"""
    
    def test_patient_record_retrieval(self):
        """Test patient record retrieval"""
        tool = PatientRecordRetrievalTool()
        result = tool._run(hospital_id="PT-001", bed_number="ICU-101")
        
        # Parse JSON result
        data = json.loads(result)
        
        assert "hospital_id" in data
        assert "bed_number" in data
        assert "medications" in data
        assert "allergies" in data
    
    def test_intent_classification_emergency(self):
        """Test emergency intent classification"""
        tool = IntentClassificationTool()
        result = tool._run(
            query="I'm having chest pain and can't breathe",
            patient_context="Patient in ICU"
        )
        
        data = json.loads(result)
        
        assert data["category"] == "EMERGENCY"
        assert data["confidence"] > 0.9
    
    def test_intent_classification_medical(self):
        """Test medical intent classification"""
        tool = IntentClassificationTool()
        result = tool._run(
            query="I need my pain medication",
            patient_context="Post-surgery patient"
        )
        
        data = json.loads(result)
        
        assert data["category"] == "MEDICAL"
        assert "medication" in data["keywords_matched"] or "pain" in data["keywords_matched"]
    
    def test_intent_classification_non_medical(self):
        """Test non-medical intent classification"""
        tool = IntentClassificationTool()
        result = tool._run(
            query="Can I have some water?",
            patient_context="Recovering patient"
        )
        
        data = json.loads(result)
        
        assert data["category"] == "NON_MEDICAL"
        assert "water" in data["keywords_matched"]
    
    def test_distress_detection_high(self):
        """Test high distress detection"""
        tool = DistressDetectionTool()
        result = tool._run(
            query="Please help me urgently, I can't take this anymore",
            conversation_history=[]
        )
        
        data = json.loads(result)
        
        assert data["distress_detected"] == True
        assert data["distress_level"] in ["MEDIUM", "HIGH"]
        assert len(data["indicators"]) > 0
    
    def test_distress_detection_none(self):
        """Test no distress detection"""
        tool = DistressDetectionTool()
        result = tool._run(
            query="What time is it?",
            conversation_history=[]
        )
        
        data = json.loads(result)
        
        assert data["distress_detected"] == False
        assert data["distress_level"] == "NONE"


class TestOrchestratorTools:
    """Tests for Central Orchestrator Agent tools"""
    
    def test_policy_evaluation_emergency(self):
        """Test policy evaluation for emergency"""
        tool = PolicyEvaluationTool()
        result = tool._run(
            intent="EMERGENCY",
            urgency="CRITICAL",
            patient_context={},
            distress_level="HIGH"
        )
        
        data = json.loads(result)
        
        assert data["escalation_level"] == "EMERGENCY"
        assert data["requires_human_approval"] == False  # Emergency skips approval
        assert "EMERGENCY_PROTOCOL" in data["applicable_policies"]
    
    def test_policy_evaluation_medical(self):
        """Test policy evaluation for medical request"""
        tool = PolicyEvaluationTool()
        result = tool._run(
            intent="MEDICAL",
            urgency="MEDIUM",
            patient_context={"original_query": "I need to see a doctor"},
            distress_level="NONE"
        )
        
        data = json.loads(result)
        
        assert data["escalation_level"] in ["NURSE", "DOCTOR"]
        assert data["requires_human_approval"] == True
        assert "MEDICAL_REQUEST_APPROVAL_REQUIRED" in data["applicable_policies"]
    
    def test_policy_evaluation_medication(self):
        """Test policy evaluation for medication request"""
        tool = PolicyEvaluationTool()
        result = tool._run(
            intent="MEDICAL",
            urgency="MEDIUM",
            patient_context={"original_query": "Can I have my medication?"},
            distress_level="NONE"
        )
        
        data = json.loads(result)
        
        assert data["requires_human_approval"] == True
        assert data["escalation_level"] == "NURSE"
        assert "MEDICATION_REQUEST_NURSE_REQUIRED" in data["applicable_policies"]
    
    def test_policy_evaluation_non_medical(self):
        """Test policy evaluation for non-medical request"""
        tool = PolicyEvaluationTool()
        result = tool._run(
            intent="NON_MEDICAL",
            urgency="LOW",
            patient_context={"original_query": "Can I have water?"},
            distress_level="NONE"
        )
        
        data = json.loads(result)
        
        assert data["requires_human_approval"] == False
        assert data["escalation_level"] == "NONE"
        assert "NON_MEDICAL_AUTO_RESPONSE" in data["applicable_policies"]
    
    def test_response_generation_emergency(self):
        """Test response generation for emergency"""
        tool = ResponseGenerationTool()
        response = tool._run(
            intent="EMERGENCY",
            patient_context="Patient in distress",
            policy_decision={"escalation_level": "EMERGENCY"},
            original_query="Chest pain"
        )
        
        assert "emergency" in response.lower()
        assert "immediately" in response.lower() or "right away" in response.lower()
    
    def test_response_generation_medication(self):
        """Test response generation for medication request"""
        tool = ResponseGenerationTool()
        response = tool._run(
            intent="MEDICAL",
            patient_context="Patient needs medication",
            policy_decision={
                "escalation_level": "NURSE",
                "requires_human_approval": True
            },
            original_query="I need my pain medication"
        )
        
        assert "nurse" in response.lower()
        assert "notified" in response.lower() or "shortly" in response.lower()
    
    def test_response_generation_water(self):
        """Test response generation for water request"""
        tool = ResponseGenerationTool()
        response = tool._run(
            intent="NON_MEDICAL",
            patient_context="Patient wants water",
            policy_decision={
                "escalation_level": "NONE",
                "requires_human_approval": False
            },
            original_query="Can I have some water?"
        )
        
        assert "water" in response.lower()
        assert len(response) > 0


class TestIntegration:
    """Integration tests for full workflow"""
    
    def test_emergency_workflow(self):
        """Test complete emergency workflow"""
        # Step 1: Intent classification
        intent_tool = IntentClassificationTool()
        intent_result = intent_tool._run(
            query="I can't breathe and have chest pain",
            patient_context="ICU patient"
        )
        intent_data = json.loads(intent_result)
        
        assert intent_data["category"] == "EMERGENCY"
        
        # Step 2: Policy evaluation
        policy_tool = PolicyEvaluationTool()
        policy_result = policy_tool._run(
            intent=intent_data["category"],
            urgency="CRITICAL",
            patient_context={},
            distress_level="HIGH"
        )
        policy_data = json.loads(policy_result)
        
        assert policy_data["escalation_level"] == "EMERGENCY"
        assert policy_data["requires_human_approval"] == False
        
        # Step 3: Response generation
        response_tool = ResponseGenerationTool()
        response = response_tool._run(
            intent=intent_data["category"],
            patient_context="Emergency situation",
            policy_decision=policy_data,
            original_query="I can't breathe and have chest pain"
        )
        
        assert len(response) > 0
        assert "emergency" in response.lower()
    
    def test_medication_workflow(self):
        """Test complete medication request workflow"""
        # Step 1: Intent classification
        intent_tool = IntentClassificationTool()
        intent_result = intent_tool._run(
            query="Can I have my pain medication?",
            patient_context="Post-surgery patient"
        )
        intent_data = json.loads(intent_result)
        
        assert intent_data["category"] == "MEDICAL"
        
        # Step 2: Policy evaluation
        policy_tool = PolicyEvaluationTool()
        policy_result = policy_tool._run(
            intent=intent_data["category"],
            urgency="MEDIUM",
            patient_context={"original_query": "Can I have my pain medication?"},
            distress_level="NONE"
        )
        policy_data = json.loads(policy_result)
        
        assert policy_data["requires_human_approval"] == True
        assert policy_data["escalation_level"] == "NURSE"
        
        # Step 3: Response generation
        response_tool = ResponseGenerationTool()
        response = response_tool._run(
            intent=intent_data["category"],
            patient_context="Medication request",
            policy_decision=policy_data,
            original_query="Can I have my pain medication?"
        )
        
        assert len(response) > 0
        assert "nurse" in response.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
