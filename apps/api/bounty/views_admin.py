from django.utils.decorators import method_decorator
from rest_framework import viewsets, generics
from .models import BountyProgram, BountySubmission
from .serializers import BountyProgramSerializer, BountySubmissionSerializer
from users.decorators import superadmin_required
from users.views_base import BaseView

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminBountyProgramListView(BaseView):
    def get(self, request):
        programs = BountyProgram.objects.all().order_by("-created_at")
        serializer = BountyProgramSerializer(programs, many=True)
        return self.success_response(serializer.data)

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminBountySubmissionListView(BaseView):
    def get(self, request):
        submissions = BountySubmission.objects.all().order_by("-created_at")
        serializer = BountySubmissionSerializer(submissions, many=True)
        return self.success_response(serializer.data)
