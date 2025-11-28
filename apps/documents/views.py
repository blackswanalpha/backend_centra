from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.documents.models import Document, Folder, DocumentCategory, DocumentAccess, FolderDocument
from .serializers import (
    DocumentSerializer, FolderSerializer, DocumentCategorySerializer,
    DocumentAccessSerializer, FolderDocumentSerializer
)


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Document model with CRUD operations and statistics.
    """
    queryset = Document.objects.select_related('category', 'uploaded_by', 'client').all()
    serializer_class = DocumentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'file_name', 'tags', 'reference_number']
    filterset_fields = ['document_type', 'category', 'access_level', 'is_active', 'client']
    ordering_fields = ['created_at', 'updated_at', 'title', 'file_size', 'expiry_date']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get document library statistics.
        GET /api/v1/documents/stats/
        """
        # Total documents
        total_documents = Document.objects.filter(is_active=True).count()
        
        # Total storage size
        total_size = Document.objects.filter(is_active=True).aggregate(
            total=Sum('file_size')
        )['total'] or 0
        
        # Documents added this month
        first_day_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        added_this_month = Document.objects.filter(
            created_at__gte=first_day_of_month,
            is_active=True
        ).count()
        
        # Expiring documents (within 30 days)
        thirty_days_from_now = timezone.now().date() + timedelta(days=30)
        expiring_documents = Document.objects.filter(
            expiry_date__lte=thirty_days_from_now,
            expiry_date__gte=timezone.now().date(),
            is_active=True
        ).count()
        
        # Pending access requests (documents with restricted access)
        pending_access_requests = DocumentAccess.objects.filter(
            permission_type='READ',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Storage usage percentage (assuming 20GB limit)
        storage_limit = 20 * 1024 * 1024 * 1024  # 20 GB in bytes
        storage_usage_percentage = (total_size / storage_limit * 100) if storage_limit > 0 else 0
        
        return Response({
            'total_documents': total_documents,
            'total_size': total_size,
            'storage_usage_percentage': round(storage_usage_percentage, 2),
            'added_this_month': added_this_month,
            'expiring_documents': expiring_documents,
            'pending_access_requests': pending_access_requests,
        })
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get recently added/updated documents.
        GET /api/v1/documents/recent/
        """
        limit = int(request.query_params.get('limit', 10))
        recent_docs = Document.objects.filter(is_active=True).order_by('-updated_at')[:limit]
        serializer = self.get_serializer(recent_docs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """
        Get documents expiring soon.
        GET /api/v1/documents/expiring/
        """
        days = int(request.query_params.get('days', 30))
        expiry_date = timezone.now().date() + timedelta(days=days)
        
        expiring_docs = Document.objects.filter(
            expiry_date__lte=expiry_date,
            expiry_date__gte=timezone.now().date(),
            is_active=True
        ).order_by('expiry_date')
        
        serializer = self.get_serializer(expiring_docs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """
        Track document download.
        POST /api/v1/documents/{id}/download/
        """
        from apps.documents.models import DocumentDownload
        
        document = self.get_object()
        
        # Create download record
        DocumentDownload.objects.create(
            document=document,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'success': True,
            'file_url': document.file.url if document.file else None
        })


class FolderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Folder model with CRUD operations.
    """
    queryset = Folder.objects.select_related('owner', 'parent_folder', 'client').all()
    serializer_class = FolderSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['is_public', 'owner', 'client', 'parent_folder']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """
        Get all documents in a folder.
        GET /api/v1/folders/{id}/documents/
        """
        folder = self.get_object()
        folder_docs = FolderDocument.objects.filter(folder=folder).select_related('document')
        documents = [fd.document for fd in folder_docs]
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_document(self, request, pk=None):
        """
        Add a document to a folder.
        POST /api/v1/folders/{id}/add_document/
        Body: {"document_id": 123}
        """
        folder = self.get_object()
        document_id = request.data.get('document_id')
        
        if not document_id:
            return Response(
                {'error': 'document_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already exists
        if FolderDocument.objects.filter(folder=folder, document=document).exists():
            return Response(
                {'error': 'Document already in folder'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create relationship
        FolderDocument.objects.create(
            folder=folder,
            document=document,
            added_by=request.user if request.user.is_authenticated else None
        )
        
        return Response({
            'success': True,
            'message': f'Document added to {folder.name}'
        })


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DocumentCategory model with CRUD operations.
    """
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class DocumentAccessViewSet(viewsets.ModelViewSet):
    """
    ViewSet for DocumentAccess model with CRUD operations.
    """
    queryset = DocumentAccess.objects.select_related('document', 'user', 'granted_by').all()
    serializer_class = DocumentAccessSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'user', 'permission_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user if self.request.user.is_authenticated else None)
