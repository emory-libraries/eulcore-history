class TaskResultAdmin(admin.ModelAdmin):
    list_display = ('object_id', 'label', 'created', 'task_start', 'task_end', 'duration')
    list_filter  = ('created',)
    # disallow creating task results via admin site
    def has_add_permission(self, request):
        return False

admin.site.register(TaskResult, TaskResultAdmin)