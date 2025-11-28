from rest_framework import serializers
from apps.documents.models import Document, Folder, DocumentCategory, DocumentAccess, FolderDocument
from django.contrib.auth.models import User


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Serializer for Document Categories"""
    
    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'description', 'parent_category', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Documents"""
    owner_name = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    file_url = serializers.SerializerMethodField()
    folder_path = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'document_type', 'category', 'category_name',
            'file', 'file_name', 'file_size', 'file_extension', 'file_url',
            'client', 'version', 'is_current_version', 'parent_document',
            'access_level', 'is_active', 'tags', 'reference_number',
            'document_date', 'expiry_date', 'uploaded_by', 'owner_name',
            'folder_path', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'uploaded_by']
    
    def get_owner_name(self, obj):
        if obj.uploaded_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}".strip() or obj.uploaded_by.username
        return "Unknown"
    
    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_folder_path(self, obj):
        # Get the folder path for this document
        folder_doc = FolderDocument.objects.filter(document=obj).first()
        if folder_doc:
            folder = folder_doc.folder
            path_parts = [folder.name]
            current = folder.parent_folder
            while current:
                path_parts.insert(0, current.name)
                current = current.parent_folder
            return '/'.join(path_parts)
        return None


class FolderSerializer(serializers.ModelSerializer):
    """Serializer for Folders"""
    owner_name = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    subfolder_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Folder
        fields = [
            'id', 'name', 'description', 'parent_folder', 'is_public',
            'owner', 'owner_name', 'client', 'document_count', 'subfolder_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner']
    
    def get_owner_name(self, obj):
        if obj.owner:
            return f"{obj.owner.first_name} {obj.owner.last_name}".strip() or obj.owner.username
        return "Unknown"
    
    def get_document_count(self, obj):
        return obj.documents.count()
    
    def get_subfolder_count(self, obj):
        return obj.subfolders.count()


class DocumentAccessSerializer(serializers.ModelSerializer):
    """Serializer for Document Access Permissions"""
    user_name = serializers.SerializerMethodField()
    granted_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentAccess
        fields = [
            'id', 'document', 'user', 'user_name', 'permission_type',
            'granted_by', 'granted_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'granted_by']
    
    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username
        return "Unknown"
    
    def get_granted_by_name(self, obj):
        if obj.granted_by:
            return f"{obj.granted_by.first_name} {obj.granted_by.last_name}".strip() or obj.granted_by.username
        return "Unknown"


class FolderDocumentSerializer(serializers.ModelSerializer):
    """Serializer for Folder-Document relationships"""
    document_title = serializers.CharField(source='document.title', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True)
    added_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = FolderDocument
        fields = [
            'id', 'folder', 'folder_name', 'document', 'document_title',
            'added_by', 'added_by_name', 'added_at'
        ]
        read_only_fields = ['id', 'added_at', 'added_by']
    
    def get_added_by_name(self, obj):
        if obj.added_by:
            return f"{obj.added_by.first_name} {obj.added_by.last_name}".strip() or obj.added_by.username
        return "Unknown"
