from django.db import models
from django.contrib.auth.models import User
from apps.clients.models import Client


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_categories'
        verbose_name_plural = 'Document Categories'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('POLICY', 'Policy'),
        ('PROCEDURE', 'Procedure'),
        ('FORM', 'Form'),
        ('TEMPLATE', 'Template'),
        ('REPORT', 'Report'),
        ('CERTIFICATE', 'Certificate'),
        ('CONTRACT', 'Contract'),
        ('INVOICE', 'Invoice'),
        ('OTHER', 'Other'),
    ]
    
    ACCESS_LEVELS = [
        ('PUBLIC', 'Public'),
        ('INTERNAL', 'Internal'),
        ('CONFIDENTIAL', 'Confidential'),
        ('RESTRICTED', 'Restricted'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, default='OTHER')
    category = models.ForeignKey(DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # File Information
    file = models.FileField(upload_to='documents/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_extension = models.CharField(max_length=10)
    
    # Relationships
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='documents')
    
    # Version Control
    version = models.CharField(max_length=20, default='1.0')
    is_current_version = models.BooleanField(default=True)
    parent_document = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='versions')
    
    # Access Control
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='INTERNAL')
    is_active = models.BooleanField(default=True)
    
    # Metadata
    tags = models.CharField(max_length=255, blank=True)  # Comma-separated tags
    reference_number = models.CharField(max_length=100, blank=True)
    
    # Dates
    document_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # System Fields
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} (v{self.version})"


class DocumentAccess(models.Model):
    PERMISSION_TYPES = [
        ('READ', 'Read'),
        ('WRITE', 'Write'),
        ('ADMIN', 'Admin'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_permissions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission_type = models.CharField(max_length=10, choices=PERMISSION_TYPES)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='access_granted')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_access'
        unique_together = ['document', 'user']
        
    def __str__(self):
        return f"{self.user.username} - {self.permission_type} - {self.document.title}"


class DocumentDownload(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='downloads')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    downloaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_downloads'
        ordering = ['-downloaded_at']
        
    def __str__(self):
        return f"{self.document.title} downloaded by {self.user.username}"


class Folder(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parent_folder = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    
    # Access Control
    is_public = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_folders')
    
    # Relationships
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='folders')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'folders'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class FolderDocument(models.Model):
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='documents')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='folders')
    
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'folder_documents'
        unique_together = ['folder', 'document']
        
    def __str__(self):
        return f"{self.document.title} in {self.folder.name}"