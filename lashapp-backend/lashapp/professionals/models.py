from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Professional(models.Model):
    """
    Perfil público de uma profissional (lash designer).
    Hoje existe apenas uma instância, mas a modelagem já suporta N
    profissionais, cada uma com seu próprio link público (slug).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professional_profile",
    )
    business_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    bio = models.TextField(blank=True)
    instagram = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "profissional"
        verbose_name_plural = "profissionais"

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.business_name)
        slug = base_slug
        counter = 1
        while Professional.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"
        return slug
