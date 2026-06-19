from rest_framework import serializers
from .models import BountyProgram, BountySubmission, BountyAttachment
from users.serializers import UserSerializer

class BountyAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BountyAttachment
        fields = ['id', 'filename', 'file_type', 'file_size', 'file_hash', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'file_hash']

class BountyProgramSerializer(serializers.ModelSerializer):
    workspace_name = serializers.ReadOnlyField(source='workspace.name')
    
    class Meta:
        model = BountyProgram
        fields = [
            'id', 'workspace', 'workspace_name', 'title', 
            'description', 'scope', 'rewards', 'status', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'workspace', 'created_at', 'updated_at']

class BountySubmissionSerializer(serializers.ModelSerializer):
    researcher_email = serializers.ReadOnlyField(source='researcher.email')
    program_title = serializers.ReadOnlyField(source='program.title')
    attachments = BountyAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = BountySubmission
        fields = [
            'id', 'program', 'program_title', 'researcher', 'researcher_email',
            'title', 'description', 'target_domain', 'severity', 'status', 
            'payout_amount', 'currency', 'proof_token', 
            'proof_verified', 'verified_at', 'created_at',
            'visual_proof_b64', 'technical_details', 'compliance_mapping',
            'verification_hash', 'compliance_certificate', 'attachments'
        ]
        read_only_fields = ['id', 'researcher', 'proof_token', 'proof_verified', 'verified_at', 'created_at', 'compliance_certificate']

class BountySubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BountySubmission
        fields = [
            'program', 'title', 'description', 'target_domain', 
            'severity', 'visual_proof_b64', 'technical_details', 'compliance_mapping'
        ]

    def validate_technical_details(self, value):
        if value is not None and not isinstance(value, dict):
            raise serializers.ValidationError("Technical details must be a valid JSON object.")
        return value

    def validate(self, data):
        severity = data.get('severity')
        tech_details = data.get('technical_details', {})
        
        # Encourage technical details for high/critical findings
        if severity in [BountySubmission.Severity.CRITICAL, BountySubmission.Severity.HIGH] and not tech_details:
            # We don't block it, but maybe we should if we want "Zero Simulation" integrity
            # For now, let's just ensure it's at least a dict
            pass
            
        return data
