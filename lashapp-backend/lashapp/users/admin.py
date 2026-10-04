from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    ordering = ["email"]
    list_display = ["email", "name", "is_professional", "is_staff", "is_active"]
    list_filter = ["is_professional", "is_staff", "is_active"]
    search_fields = ["email", "name"]
    
    # 1. Regista a nova ação customizada no menu dropdown do painel
    actions = ["desativar_usuarios"]
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {"fields": ("name", "phone")}),
        (
            "Permissões",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_professional",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )

    # --- INÍCIO DA LÓGICA DE SOFT DELETE ---

    @admin.action(description="Desativar utilizadores selecionados (Sem apagar dados)")
    def desativar_usuarios(self, request, queryset):
        """Ação que substitui o apagar em massa. Apenas desativa a conta."""
        queryset.update(is_active=False)
        self.message_user(request, "Utilizadores desativados com sucesso. Fichas e agendamentos foram mantidos.")

    def get_actions(self, request):
        """Remove a ação padrão 'Remover selecionados' do Django para evitar o erro de cascata."""
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        """Remove o botão vermelho 'Apagar' do canto inferior esquerdo na página de edição."""
        return False
        
    # --- FIM DA LÓGICA DE SOFT DELETE ---