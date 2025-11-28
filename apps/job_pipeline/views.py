from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

from .models import JobPipeline, PipelineStageTransition, PipelineMilestone
from .serializers import (
    JobPipelineSerializer, 
    JobPipelineDetailSerializer,
    PipelineStageTransitionSerializer,
    PipelineMilestoneSerializer,
    JobPipelineStatsSerializer
)
from apps.business_development.models import Lead, Opportunity, Contract
from apps.audits.models import Audit


class JobPipelineViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job pipelines
    """
    queryset = JobPipeline.objects.all()
    serializer_class = JobPipelineSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return JobPipelineDetailSerializer
        return JobPipelineSerializer
    
    def get_queryset(self):
        queryset = JobPipeline.objects.select_related(
            'lead', 'opportunity', 'contract', 'owner', 'created_by'
        ).prefetch_related('milestones', 'stage_transitions')
        
        # Filter parameters
        stage = self.request.query_params.get('stage')
        status = self.request.query_params.get('status')
        owner = self.request.query_params.get('owner')
        client = self.request.query_params.get('client')
        search = self.request.query_params.get('search')
        
        if stage:
            queryset = queryset.filter(current_stage=stage)
        if status:
            queryset = queryset.filter(status=status)
        if owner:
            queryset = queryset.filter(owner_id=owner)
        if client:
            queryset = queryset.filter(client_name__icontains=client)
        if search:
            queryset = queryset.filter(
                Q(pipeline_id__icontains=search) |
                Q(client_name__icontains=search) |
                Q(service_description__icontains=search)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def advance_stage(self, request, pk=None):
        """Advance pipeline to next stage"""
        pipeline = self.get_object()
        new_stage = request.data.get('stage')
        
        if not new_stage:
            return Response(
                {'error': 'Stage is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                pipeline.advance_stage(new_stage, request.user)
                serializer = self.get_serializer(pipeline)
                return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def link_object(self, request, pk=None):
        """Link a business object (lead, opportunity, contract, audit) to pipeline"""
        pipeline = self.get_object()
        object_type = request.data.get('object_type')  # 'lead', 'opportunity', 'contract', 'audit'
        object_id = request.data.get('object_id')
        
        if not object_type or not object_id:
            return Response(
                {'error': 'object_type and object_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                if object_type == 'lead':
                    obj = Lead.objects.get(id=object_id)
                    pipeline.lead = obj
                elif object_type == 'opportunity':
                    obj = Opportunity.objects.get(id=object_id)
                    pipeline.opportunity = obj
                elif object_type == 'contract':
                    obj = Contract.objects.get(id=object_id)
                    pipeline.contract = obj
                elif object_type == 'audit':
                    obj = Audit.objects.get(id=object_id)
                    obj.pipeline = pipeline
                    obj.save()
                else:
                    return Response(
                        {'error': 'Invalid object_type'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Update pipeline based on linked object
                pipeline.update_from_related_object(obj, request.user)
                
                serializer = self.get_serializer(pipeline)
                return Response(serializer.data)
                
        except (Lead.DoesNotExist, Opportunity.DoesNotExist, Contract.DoesNotExist, Audit.DoesNotExist):
            return Response(
                {'error': 'Object not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get pipeline statistics"""
        queryset = self.get_queryset()
        
        # Stage distribution
        stage_stats = queryset.values('current_stage').annotate(
            count=Count('id'),
            total_value=Sum('estimated_value')
        ).order_by('current_stage')
        
        # Status distribution
        status_stats = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Average time in stages
        avg_stage_time = queryset.exclude(
            current_stage='LEAD'
        ).aggregate(
            avg_days=Avg('days_in_current_stage')
        )
        
        # Monthly trend (last 12 months)
        twelve_months_ago = timezone.now() - timedelta(days=365)
        monthly_stats = []
        for i in range(12):
            month_start = twelve_months_ago + timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            month_data = queryset.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(
                count=Count('id'),
                total_value=Sum('estimated_value') or 0
            )
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'count': month_data['count'],
                'total_value': month_data['total_value']
            })
        
        # Top performers
        top_owners = queryset.filter(
            owner__isnull=False
        ).values(
            'owner__id', 
            'owner__first_name', 
            'owner__last_name'
        ).annotate(
            pipeline_count=Count('id'),
            total_value=Sum('estimated_value') or 0
        ).order_by('-total_value')[:10]
        
        stats_data = {
            'total_pipelines': queryset.count(),
            'total_value': queryset.aggregate(Sum('estimated_value'))['estimated_value__sum'] or 0,
            'stage_distribution': stage_stats,
            'status_distribution': status_stats,
            'average_stage_time': avg_stage_time['avg_days'] or 0,
            'monthly_trend': monthly_stats,
            'top_owners': top_owners,
        }
        
        serializer = JobPipelineStatsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard data for pipeline overview"""
        queryset = self.get_queryset()
        
        # Quick stats
        active_count = queryset.filter(status='ACTIVE').count()
        on_hold_count = queryset.filter(status='ON_HOLD').count()
        completed_count = queryset.filter(status='COMPLETED').count()
        
        # Current stage breakdown
        stages = queryset.filter(status='ACTIVE').values('current_stage').annotate(
            count=Count('id')
        ).order_by('current_stage')
        
        # Upcoming milestones (next 30 days)
        thirty_days = timezone.now().date() + timedelta(days=30)
        upcoming_milestones = PipelineMilestone.objects.filter(
            pipeline__in=queryset,
            is_completed=False,
            due_date__lte=thirty_days
        ).select_related('pipeline').order_by('due_date')[:10]
        
        # Overdue milestones
        overdue_milestones = PipelineMilestone.objects.filter(
            pipeline__in=queryset,
            is_completed=False,
            due_date__lt=timezone.now().date()
        ).select_related('pipeline').count()
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_transitions = PipelineStageTransition.objects.filter(
            pipeline__in=queryset,
            transitioned_at__gte=week_ago
        ).select_related('pipeline', 'transitioned_by').order_by('-transitioned_at')[:10]
        
        return Response({
            'quick_stats': {
                'active': active_count,
                'on_hold': on_hold_count,
                'completed': completed_count,
                'total': queryset.count()
            },
            'stage_breakdown': stages,
            'upcoming_milestones': PipelineMilestoneSerializer(upcoming_milestones, many=True).data,
            'overdue_count': overdue_milestones,
            'recent_activity': PipelineStageTransitionSerializer(recent_transitions, many=True).data
        })
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get timeline view of pipeline progression"""
        pipeline = self.get_object()
        
        # Get all stage transitions
        transitions = pipeline.stage_transitions.select_related('transitioned_by').order_by('transitioned_at')
        
        # Get milestones
        milestones = pipeline.milestones.all().order_by('due_date')
        
        # Create timeline events
        timeline_events = []
        
        # Add transitions
        for transition in transitions:
            timeline_events.append({
                'type': 'transition',
                'date': transition.transitioned_at.isoformat(),
                'title': f"Advanced from {transition.from_stage} to {transition.to_stage}",
                'description': transition.notes,
                'user': transition.transitioned_by.get_full_name() if transition.transitioned_by else None,
                'data': PipelineStageTransitionSerializer(transition).data
            })
        
        # Add milestones
        for milestone in milestones:
            timeline_events.append({
                'type': 'milestone',
                'date': milestone.due_date.isoformat(),
                'title': milestone.title,
                'description': milestone.description,
                'completed': milestone.is_completed,
                'overdue': milestone.is_overdue,
                'data': PipelineMilestoneSerializer(milestone).data
            })
        
        # Sort by date
        timeline_events.sort(key=lambda x: x['date'])
        
        return Response({
            'pipeline_id': pipeline.pipeline_id,
            'client_name': pipeline.client_name,
            'current_stage': pipeline.current_stage,
            'timeline': timeline_events
        })


class PipelineMilestoneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing pipeline milestones
    """
    queryset = PipelineMilestone.objects.all()
    serializer_class = PipelineMilestoneSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    
    def get_queryset(self):
        queryset = PipelineMilestone.objects.select_related('pipeline', 'assigned_to')
        
        # Filter parameters
        pipeline = self.request.query_params.get('pipeline')
        milestone_type = self.request.query_params.get('type')
        completed = self.request.query_params.get('completed')
        overdue = self.request.query_params.get('overdue')
        assigned_to = self.request.query_params.get('assigned_to')
        
        if pipeline:
            queryset = queryset.filter(pipeline_id=pipeline)
        if milestone_type:
            queryset = queryset.filter(milestone_type=milestone_type)
        if completed is not None:
            is_completed = completed.lower() == 'true'
            queryset = queryset.filter(is_completed=is_completed)
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(
                is_completed=False,
                due_date__lt=timezone.now().date()
            )
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark milestone as completed"""
        milestone = self.get_object()
        
        with transaction.atomic():
            milestone.is_completed = True
            milestone.completed_date = timezone.now().date()
            milestone.save()
            
            # Check if this completion triggers pipeline advancement
            pipeline = milestone.pipeline
            if milestone.milestone_type == 'CONTRACT_SIGNATURE' and pipeline.current_stage == 'OPPORTUNITY':
                try:
                    pipeline.advance_stage('CONTRACT', request.user)
                except ValueError:
                    pass  # Stage advancement may not be valid
            
            serializer = self.get_serializer(milestone)
            return Response(serializer.data)


class PipelineStageTransitionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing stage transition history
    """
    queryset = PipelineStageTransition.objects.all()
    serializer_class = PipelineStageTransitionSerializer
    permission_classes = [AllowAny]  # Change to IsAuthenticated in production
    
    def get_queryset(self):
        queryset = PipelineStageTransition.objects.select_related('pipeline', 'transitioned_by')
        
        pipeline = self.request.query_params.get('pipeline')
        if pipeline:
            queryset = queryset.filter(pipeline_id=pipeline)
        
        return queryset