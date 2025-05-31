from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Question, Answer, UserUsage


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'patronymic', 'personal_code', 'birth_date', 'is_active', 'created_at']
    list_filter = ['is_active']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'patronymic', 'birth_date', 'profile_picture', 'phone_number', 'address', 'personal_code')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'patronymic', 'birth_date', 'profile_picture', 'phone_number', 'address', 'personal_code', 'is_active'),
        }),
    )

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 1

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'added_by', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['text']
    inlines = [AnswerInline]

class AnswerAdmin(admin.ModelAdmin):
    list_display = ['text', 'question', 'is_correct', 'added_by', 'is_active', 'created_at']
    list_filter = ['is_correct', 'is_active']
    search_fields = ['text', 'question__text']

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)


@admin.register(UserUsage)
class UserUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'usage_count', 'last_used', 'created_at')  # Jadvaldagi ustunlar
    list_filter = ('last_used', 'created_at')  # Yon panelda filtrlash
    search_fields = ('user__username', 'user__full_name', 'user__email')  # Qidiruv
    ordering = ('-last_used',)  # Default tartiblash: oxirgi foydalanish bo‘yicha
    readonly_fields = ('last_used', 'created_at')  # Bu maydonlar tahrirlanmaydi
    date_hierarchy = 'last_used'  # Admin panelda yuqorida vaqt bo‘yicha filtrlash
    list_per_page = 25  # Har bir sahifada nechtadan yozuv ko‘rsatiladi

    fieldsets = (
        (None, {
            'fields': ('user', 'usage_count')
        }),
        ('Vaqt maʼlumotlari', {
            'fields': ('last_used', 'created_at'),
            'classes': ('collapse',),
            'description': 'Bu maydonlar avtomatik ravishda yangilanadi.'
        }),
    )

    def get_queryset(self, request):
        """Optimize qilingan queryset, related user bilan birga"""
        return super().get_queryset(request).select_related('user')