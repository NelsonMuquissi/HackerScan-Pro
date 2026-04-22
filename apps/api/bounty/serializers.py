from rest_framework import serializers
from .models import BountyProgram, BountySubmission
from users.serializers import UserSerializer

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
    
    class Meta:
        model = BountySubmission
        fields = [
            'id', 'program', 'program_title', 'researcher', 'researcher_email',
            'title', 'description', 'target_domain', 'severity', 'status', 
            'payout_amount', 'currency', 'proof_token', 
            'proof_verified', 'verified_at', 'created_at'
        ]
        read_only_fields = ['id', 'researcher', 'proof_token', 'proof_verified', 'verified_at', 'created_at']

class BountySubmissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BountySubmission
        fields = ['program', 'title', 'description', 'target_domain', 'severity']
